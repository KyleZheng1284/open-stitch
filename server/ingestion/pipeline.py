"""Ingestion pipeline — download, extract, parallel ASR + VLM + summary."""
from __future__ import annotations

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


async def ingest_video(video_path: str, dense_fps: int = 4, window_s: int = 5) -> dict:
    """Full ingestion of a single video. Returns summary, asr, vlm, timeline."""
    s = get_settings()
    info = get_video_info(video_path)
    duration = info["duration"]

    logger.info("Ingesting %s (%.1fs, %dx%d)", video_path, duration, info["width"], info["height"])

    # Step 1: Extract frames + audio in parallel
    with ThreadPoolExecutor(max_workers=3) as pool:
        dense_fut = pool.submit(extract_frames, video_path, dense_fps)
        summary_fut = pool.submit(extract_frames, video_path, s.summary_fps)
        audio_fut = pool.submit(extract_audio, video_path)
        dense_frames = dense_fut.result()
        summary_frames = summary_fut.result()
        audio_path = audio_fut.result()

    dense_uris = [encode_frame(f) for f in dense_frames]
    summary_uris = [encode_frame(f) for f in summary_frames]

    # Step 2: ASR + dense VLM + fast summary in parallel
    asr_result = None
    vlm_results = None
    summary_text = None

    def asr_task():
        nonlocal asr_result
        asr_result = run_whisper(audio_path)

    def vlm_task():
        nonlocal vlm_results
        vlm_results = run_vlm(dense_uris, dense_fps, window_s, duration)

    def summary_task():
        nonlocal summary_text
        summary_text = run_fast_summary(summary_uris, duration)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(f) for f in [summary_task, asr_task, vlm_task]]
        for f in futs:
            f.result()

    # Step 3: Merge timeline
    timeline = merge_timeline(asr_result, vlm_results)

    return {
        "video_path": video_path,
        "duration_s": duration,
        "info": info,
        "summary": summary_text,
        "asr": asr_result,
        "vlm_windows": vlm_results,
        "timeline": timeline,
    }


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
