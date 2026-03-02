"""Ingestion pipeline — download, extract, parallel ASR + VLM + summary."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from server.config import get_settings
from server.ingestion.asr import run_whisper
from server.ingestion.summary import run_fast_summary
from server.ingestion.vlm import run_vlm

logger = logging.getLogger(__name__)


def get_video_info(video_path: str) -> dict:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    for s in data.get("streams", []):
        if s["codec_type"] == "video":
            return {
                "duration": duration,
                "width": int(s["width"]),
                "height": int(s["height"]),
                "fps": eval(s.get("r_frame_rate", "30/1")),
            }
    return {"duration": duration, "width": 0, "height": 0, "fps": 30}


def extract_frames(video_path: str, fps: int = 4) -> list[Path]:
    tmpdir = tempfile.mkdtemp(prefix="av_frames_")
    out_pattern = str(Path(tmpdir) / "frame_%05d.jpg")
    cmd = ["ffmpeg", "-i", video_path, "-vf", f"fps={fps},scale=768:-1", "-q:v", "3", "-y", out_pattern]
    subprocess.run(cmd, capture_output=True, check=True)
    return sorted(Path(tmpdir).glob("frame_*.jpg"))


def extract_audio(video_path: str) -> Path:
    tmpdir = tempfile.mkdtemp(prefix="av_audio_")
    audio_path = Path(tmpdir) / "audio.wav"
    cmd = ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", str(audio_path)]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path


def encode_frame(frame_path: Path) -> str:
    b64 = base64.b64encode(frame_path.read_bytes()).decode()
    return f"data:image/jpeg;base64,{b64}"


def merge_timeline(asr_result: dict, vlm_windows: list[dict]) -> list[dict]:
    """Merge word-level ASR and per-second VLM into unified timeline."""
    vlm_seconds = {}
    for w in vlm_windows:
        for s in w.get("seconds", []):
            vlm_seconds[int(s.get("t", 0))] = s

    word_by_second: dict[int, list] = {}
    for w in asr_result.get("words", []):
        sec = int(w["start"])
        word_by_second.setdefault(sec, []).append(w)

    all_seconds = sorted(set(list(vlm_seconds.keys()) + list(word_by_second.keys())))
    timeline = []
    for sec in all_seconds:
        entry = {"t": sec}
        if sec in vlm_seconds:
            v = vlm_seconds[sec]
            entry.update({
                "action": v.get("action", ""),
                "energy": v.get("energy", 0),
                "edit_signal": v.get("edit_signal", "hold"),
                "meme_potential": v.get("meme_potential", 0),
                "subjects": v.get("subjects", []),
                "face": v.get("face", {}),
                "motion": v.get("motion", {}),
            })
        if sec in word_by_second:
            words = word_by_second[sec]
            entry["speech"] = " ".join(w["word"] for w in words)
            entry["word_count"] = len(words)
            entry["avg_confidence"] = round(sum(w["confidence"] for w in words) / len(words), 2)
        else:
            entry["speech"] = ""
            entry["word_count"] = 0
        timeline.append(entry)
    return timeline


def _ingest_video_summary_sync(video_path: str) -> dict:
    s = get_settings()
    info = get_video_info(video_path)
    duration = info["duration"]

    logger.info("Fast summary for %s (%.1fs)", video_path, duration)

    with ThreadPoolExecutor(max_workers=2) as pool:
        summary_fut = pool.submit(extract_frames, video_path, s.summary_fps)
        audio_fut = pool.submit(extract_audio, video_path)
        summary_frames = summary_fut.result()
        audio_path = audio_fut.result()

    summary_uris = [encode_frame(f) for f in summary_frames]
    summary_text = run_fast_summary(summary_uris, duration)

    logger.info("Summary ready for %s (%d chars)", video_path, len(summary_text))

    return {
        "video_path": video_path,
        "duration_s": duration,
        "info": info,
        "summary": summary_text,
        "asr": None,
        "vlm_windows": None,
        "timeline": [],
        "_audio_path": str(audio_path),
    }


async def ingest_video_summary(video_path: str) -> dict:
    """Fast pass: extract summary frames + run Flash Lite summary (~10-20s).

    Returns partial ingestion data with summary, duration, and info.
    Runs blocking work in a thread to keep the event loop responsive.
    """
    return await asyncio.to_thread(_ingest_video_summary_sync, video_path)


def _ingest_video_deep_sync(partial: dict, dense_fps: int = 4, window_s: int = 5) -> dict:
    video_path = partial["video_path"]
    duration = partial["duration_s"]
    audio_path = Path(partial.get("_audio_path", ""))

    logger.info("Deep analysis for %s (ASR + VLM @ %dfps)", video_path, dense_fps)

    dense_frames = extract_frames(video_path, dense_fps)
    dense_uris = [encode_frame(f) for f in dense_frames]

    if not audio_path.exists():
        audio_path = extract_audio(video_path)

    asr_result = None
    vlm_results = None

    def asr_task():
        nonlocal asr_result
        asr_result = run_whisper(audio_path)

    def vlm_task():
        nonlocal vlm_results
        vlm_results = run_vlm(dense_uris, dense_fps, window_s, duration)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(f) for f in [asr_task, vlm_task]]
        for f in futs:
            f.result()

    timeline = merge_timeline(asr_result, vlm_results)

    partial["asr"] = asr_result
    partial["vlm_windows"] = vlm_results
    partial["timeline"] = timeline
    partial.pop("_audio_path", None)

    logger.info(
        "Deep analysis done for %s -- ASR=%d words, VLM=%d timeline entries",
        video_path, len(asr_result.get("words", [])), len(timeline),
    )
    return partial


async def ingest_video_deep(partial: dict, dense_fps: int = 4, window_s: int = 5) -> dict:
    """Deep pass: run ASR + dense VLM on a video that already has a summary.

    Mutates and returns the partial dict with full ASR, VLM, and merged timeline.
    Runs blocking work in a thread to keep the event loop responsive.
    """
    return await asyncio.to_thread(_ingest_video_deep_sync, partial, dense_fps, window_s)


def _ingest_image_sync(image_path: str) -> dict:
    from server.ingestion.summary import run_image_summary

    path = Path(image_path)
    image_uri = encode_frame(path)

    try:
        from PIL import Image
        with Image.open(path) as img:
            width, height = img.size
    except Exception:
        width, height = 0, 0

    summary = run_image_summary(image_uri)

    logger.info("Image summary ready for %s (%d chars)", image_path, len(summary))

    return {
        "image_path": image_path,
        "video_path": image_path,
        "duration_s": 0,
        "info": {"width": width, "height": height, "fps": 0, "duration": 0},
        "summary": summary,
        "asr": None,
        "vlm_windows": None,
        "timeline": [],
        "media_type": "image",
    }


async def ingest_image_summary(image_path: str) -> dict:
    """Describe a single image via VLM. Returns ingestion data compatible with video format."""
    return await asyncio.to_thread(_ingest_image_sync, image_path)


async def ingest_video(video_path: str, dense_fps: int = 4, window_s: int = 5) -> dict:
    """Full ingestion (summary + deep) in one call. For backwards compat."""
    partial = await ingest_video_summary(video_path)
    return await ingest_video_deep(partial, dense_fps, window_s)


async def ingest_project(project: dict) -> dict:
    """Ingest all videos in a project. Returns {video_id: ingestion_data}."""
    results = {}
    for vid in project.get("videos", []):
        local_path = vid.local_path if hasattr(vid, "local_path") else vid.get("local_path", "")
        if not local_path:
            # Try to find by filename in data/downloads
            local_path = f"data/downloads/{vid.filename if hasattr(vid, 'filename') else vid.get('filename', vid.id)}"

        data = await ingest_video(local_path)
        results[vid.id if hasattr(vid, "id") else vid["id"]] = data
    return results
