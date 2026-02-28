"""Open-Stitch ingestion test — parallel ASR + VLM with timing.

Runs Whisper ASR and Gemini VLM concurrently on the same video,
then merges the results into a unified timeline for the edit planner.

Usage: .venv/bin/python tools/test_ingestion.py data/IMG_1103.MOV [--fps 4]
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY", "")
BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://inference-api.nvidia.com/v1")
MODEL = os.getenv("VLM_MODEL", "gcp/google/gemini-3-pro")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gcp/google/gemini-2.5-flash-lite")
SUMMARY_FPS = int(os.getenv("SUMMARY_FPS", "2"))

# Whisper model — use "tiny" for fast CPU testing, "large-v3-turbo" for production
WHISPER_MODEL = os.getenv("ASR_MODEL_SIZE", "small")
WHISPER_DEVICE = "cpu"  # no CUDA on this machine
WHISPER_COMPUTE = "int8"


# ── Timing helper ──
class Timer:
    def __init__(self, label: str):
        self.label = label
        self.elapsed = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self._start
        print(f"  [{self.label}] {self.elapsed:.2f}s")


# ── FFmpeg helpers ──

def get_video_info(video_path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
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
    tmpdir = tempfile.mkdtemp(prefix="os_frames_")
    out_pattern = str(Path(tmpdir) / "frame_%05d.jpg")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={fps},scale=768:-1",
        "-q:v", "3", "-y", out_pattern,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return sorted(Path(tmpdir).glob("frame_*.jpg"))


def extract_audio(video_path: str) -> Path:
    tmpdir = tempfile.mkdtemp(prefix="os_audio_")
    audio_path = Path(tmpdir) / "audio.wav"
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-y", str(audio_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path


def encode_frame(frame_path: Path) -> str:
    data = frame_path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/jpeg;base64,{b64}"


def parse_json_response(content: str) -> dict:
    clean = content.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"raw": content}


# ── ASR (Whisper) ──

def run_whisper(audio_path: Path) -> list[dict]:
    """Run Whisper ASR and return word-level segments with timestamps."""
    from faster_whisper import WhisperModel

    with Timer("Whisper model load"):
        model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)

    with Timer("Whisper transcription"):
        segments, info = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language="en",
        )
        segments = list(segments)

    print(f"  Language: {info.language} (prob: {info.language_probability:.2f})")

    # Flatten to word-level
    words = []
    for seg in segments:
        for w in (seg.words or []):
            words.append({
                "word": w.word.strip(),
                "start": round(w.start, 2),
                "end": round(w.end, 2),
                "confidence": round(w.probability, 2),
            })

    # Also build sentence-level segments
    sentences = []
    for seg in segments:
        sentences.append({
            "text": seg.text.strip(),
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
        })

    return {"words": words, "sentences": sentences, "language": info.language}


# ── VLM (Gemini via NIM) ──

def call_vlm(client: httpx.Client, messages: list, max_tokens: int = 4096) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = client.post(f"{BASE_URL}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def analyze_window(
    client: httpx.Client,
    frame_uris: list[str],
    window_start_s: float,
    fps: int,
    duration: float,
) -> dict:
    content_parts: list[dict] = [
        {"type": "text", "text": (
            f"Analyze these {len(frame_uris)} frames "
            f"(seconds {window_start_s:.1f}-{window_start_s + len(frame_uris)/fps:.1f} "
            f"of {duration:.0f}s video, {fps} FPS).\n\n"
            "Return JSON with:\n"
            "- seconds: list of per-second objects:\n"
            "    - t: timestamp (float)\n"
            "    - action: specific description of motion/gestures/expressions\n"
            "    - subjects: [{name, position: left/center/right, distance: close/mid/far}]\n"
            "    - motion: {direction, speed: slow/medium/fast, type: walk/gesture/turn/still}\n"
            "    - energy: 0.0-1.0\n"
            "    - edit_signal: hold/cut/zoom_in/zoom_out/slow_mo/speed_up/add_meme/transition/emphasize\n"
            "    - meme_potential: 0.0-1.0\n"
            "    - face: {visible: bool, expression: string, looking_at: camera/away/down}\n"
            "- window_summary: one sentence\n"
            "- peak_moment: timestamp with highest interest\n\n"
            "Be PRECISE about frame-to-frame changes. Return ONLY valid JSON."
        )},
    ]
    for i, uri in enumerate(frame_uris):
        t = window_start_s + i / fps
        content_parts.append({"type": "text", "text": f"[t={t:.2f}s]"})
        content_parts.append({"type": "image_url", "image_url": {"url": uri}})

    raw = call_vlm(client, [{"role": "user", "content": content_parts}])
    return parse_json_response(raw)


def run_vlm(frame_uris: list[str], fps: int, window_s: int, duration: float) -> list[dict]:
    """Run VLM analysis across all windows."""
    client = httpx.Client(
        timeout=180.0,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    frames_per_window = fps * window_s
    num_windows = (len(frame_uris) + frames_per_window - 1) // frames_per_window

    results = []
    for w in range(num_windows):
        start_idx = w * frames_per_window
        end_idx = min(start_idx + frames_per_window, len(frame_uris))
        window_uris = frame_uris[start_idx:end_idx]
        window_start_s = start_idx / fps

        print(f"\n  Window {w+1}/{num_windows} (t={window_start_s:.1f}-{window_start_s + len(window_uris)/fps:.1f}s)")
        with Timer(f"VLM window {w+1}"):
            result = analyze_window(client, window_uris, window_start_s, fps, duration)

        if "window_summary" in result:
            print(f"    {result['window_summary']}")
        for s in result.get("seconds", []):
            e = "#" * int(s.get("energy", 0) * 10)
            sig = s.get("edit_signal", "-")
            act = s.get("action", "")[:55]
            print(f"    t={s.get('t','?'):>5}s  E[{e:<10}] {sig:<12} {act}")

        results.append(result)
    return results


# ── Fast summary (Flash Lite) ──

def run_fast_summary(frame_uris: list[str], duration: float) -> str:
    """Single-call video summary on Flash Lite at 2 FPS. Returns paragraph."""
    client = httpx.Client(
        timeout=120.0,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    content_parts: list[dict] = [
        {"type": "text", "text": (
            f"These are {len(frame_uris)} frames sampled at {SUMMARY_FPS} FPS from a "
            f"{duration:.0f}-second video.\n\n"
            "Write a concise 1-paragraph summary of what happens in this video. "
            "Include: who/what is in it, key actions/events in order, "
            "the setting/location, and the overall mood/vibe. "
            "Be specific about timing (beginning, middle, end)."
        )},
    ]
    for i, uri in enumerate(frame_uris):
        t = i / SUMMARY_FPS
        content_parts.append({"type": "text", "text": f"[t={t:.1f}s]"})
        content_parts.append({"type": "image_url", "image_url": {"url": uri}})

    payload = {
        "model": SUMMARY_MODEL,
        "messages": [{"role": "user", "content": content_parts}],
        "temperature": 0.3,
        "max_tokens": 512,
        "stream": False,
    }
    resp = client.post(f"{BASE_URL}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ── Merge ASR + VLM into unified timeline ──

def merge_timeline(asr_result: dict, vlm_windows: list[dict]) -> list[dict]:
    """Merge word-level ASR and per-second VLM into a unified timeline."""
    # Collect all VLM seconds
    vlm_seconds = {}
    for w in vlm_windows:
        for s in w.get("seconds", []):
            t = s.get("t", 0)
            vlm_seconds[int(t)] = s

    # Align words to seconds
    word_by_second: dict[int, list] = {}
    for w in asr_result.get("words", []):
        sec = int(w["start"])
        word_by_second.setdefault(sec, []).append(w)

    # Build merged timeline
    all_seconds = sorted(set(list(vlm_seconds.keys()) + list(word_by_second.keys())))
    timeline = []
    for sec in all_seconds:
        entry = {"t": sec}

        # VLM data
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

        # ASR data
        if sec in word_by_second:
            words = word_by_second[sec]
            entry["speech"] = " ".join(w["word"] for w in words)
            entry["word_count"] = len(words)
            entry["avg_confidence"] = round(
                sum(w["confidence"] for w in words) / len(words), 2
            )
        else:
            entry["speech"] = ""
            entry["word_count"] = 0

        timeline.append(entry)

    return timeline


# ── Edit planner ──

def generate_edit_plan(
    client: httpx.Client,
    timeline: list[dict],
    asr_result: dict,
    duration: float,
) -> dict:
    """Generate edit plan from merged ASR+VLM timeline."""
    # Full transcript for context
    full_text = " ".join(s["text"] for s in asr_result.get("sentences", []))

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Director Agent for Open-Stitch, an AI video editor. "
                "You receive a merged timeline of visual analysis + speech transcription "
                "and produce a final TikTok/Reels-ready edit plan."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Video duration: {duration:.0f}s\n\n"
                f"Full transcript: \"{full_text}\"\n\n"
                f"Per-second timeline (merged VLM + ASR):\n{json.dumps(timeline, indent=1)}\n\n"
                "Produce a JSON edit plan:\n"
                "- title: catchy title\n"
                "- vibe: 3-5 word aesthetic\n"
                "- clips: [{start_s, end_s, reason, edits: [{type, at_s, params}]}]\n"
                "  edit types: cut/zoom_in/zoom_out/slow_mo/speed_up/transition/meme_overlay/text_overlay\n"
                "- subtitles: [{start_s, end_s, text, style: word_by_word|sentence|karaoke}]\n"
                "  Use the ACTUAL transcript words with precise timestamps\n"
                "- meme_overlays: [{at_s, text, position, style}]\n"
                "- subtitle_style: tiktok_pop/minimal/karaoke/outline\n"
                "- music: {mood, energy, genre}\n"
                "- sfx: [{at_s, sound, reason}]\n\n"
                "IMPORTANT: Use the speech transcript to create subtitles with exact word timing. "
                "Align edits with both speech rhythm and visual moments.\n"
                "Return ONLY valid JSON."
            ),
        },
    ]
    raw = call_vlm(client, messages, max_tokens=8192)
    return parse_json_response(raw)


# ── Main ──

def main():
    global WHISPER_MODEL

    parser = argparse.ArgumentParser(description="Open-Stitch ingestion test")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--fps", type=int, default=4, help="Frames per second (default: 4)")
    parser.add_argument("--window", type=int, default=5, help="VLM window size in seconds (default: 5)")
    parser.add_argument("--whisper-model", default=WHISPER_MODEL, help=f"Whisper model size (default: {WHISPER_MODEL})")
    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"File not found: {args.video}")
        sys.exit(1)
    if not API_KEY:
        print("Set NVIDIA_API_KEY in .env")
        sys.exit(1)

    info = get_video_info(args.video)
    duration = info["duration"]
    fps = args.fps
    window_s = args.window
    WHISPER_MODEL = args.whisper_model

    total_start = time.perf_counter()

    print(f"\n{'='*70}")
    print(f"OPEN-STITCH INGESTION — PARALLEL ASR + VLM + SUMMARY")
    print(f"  Video:      {args.video}")
    print(f"  Duration:   {duration:.1f}s ({info['width']}x{info['height']} @ {info['fps']:.0f}fps)")
    print(f"  Dense VLM:  {MODEL} @ {fps} FPS, {window_s}s windows")
    print(f"  Summary:    {SUMMARY_MODEL} @ {SUMMARY_FPS} FPS (single call)")
    print(f"  ASR:        Whisper {WHISPER_MODEL} on {WHISPER_DEVICE}")
    print(f"{'='*70}")

    # ── Step 1: Extract dense frames + summary frames + audio in parallel ──
    print(f"\n[1/6] Extracting dense frames + summary frames + audio (parallel)...")
    with Timer("Frame + summary frame + audio extraction"):
        with ThreadPoolExecutor(max_workers=3) as pool:
            frame_future = pool.submit(extract_frames, args.video, fps)
            summary_frame_future = pool.submit(extract_frames, args.video, SUMMARY_FPS)
            audio_future = pool.submit(extract_audio, args.video)
            frames = frame_future.result()
            summary_frames = summary_frame_future.result()
            audio_path = audio_future.result()

    print(f"  Dense: {len(frames)} frames @ {fps} FPS")
    print(f"  Summary: {len(summary_frames)} frames @ {SUMMARY_FPS} FPS")
    print(f"  Audio: {audio_path.stat().st_size / 1024:.0f} KB")
    frame_uris = [encode_frame(f) for f in frames]
    summary_uris = [encode_frame(f) for f in summary_frames]

    # ── Step 2: ASR + Dense VLM + Fast Summary in parallel ──
    print(f"\n[2/6] Running ASR + Dense VLM + Fast Summary in parallel...")
    print(f"  ASR: Whisper {WHISPER_MODEL}...")
    print(f"  Dense VLM: {MODEL} ({len(frame_uris)} frames, {(len(frame_uris) + fps*window_s - 1) // (fps*window_s)} windows)...")
    print(f"  Fast Summary: {SUMMARY_MODEL} ({len(summary_uris)} frames, 1 call)...")

    asr_result = None
    vlm_results = None
    summary_text = None
    summary_time = 0.0

    def asr_task():
        nonlocal asr_result
        print(f"\n  --- ASR START ---")
        asr_result = run_whisper(audio_path)
        print(f"  --- ASR DONE: {len(asr_result['words'])} words, {len(asr_result['sentences'])} sentences ---")

    def vlm_task():
        nonlocal vlm_results
        print(f"\n  --- DENSE VLM START ---")
        vlm_results = run_vlm(frame_uris, fps, window_s, duration)
        print(f"\n  --- DENSE VLM DONE: {len(vlm_results)} windows ---")

    def summary_task():
        nonlocal summary_text, summary_time
        print(f"\n  --- FAST SUMMARY START ---")
        t0 = time.perf_counter()
        summary_text = run_fast_summary(summary_uris, duration)
        summary_time = time.perf_counter() - t0
        print(f"  --- FAST SUMMARY DONE: {summary_time:.2f}s ---")
        print(f"\n  >> SUMMARY (ready for clarifying agent):")
        print(f"  >> {summary_text}")

    with Timer("Parallel ASR + Dense VLM + Fast Summary"):
        with ThreadPoolExecutor(max_workers=3) as pool:
            summary_fut = pool.submit(summary_task)
            asr_fut = pool.submit(asr_task)
            vlm_fut = pool.submit(vlm_task)
            # Summary finishes first — clarifying agent could start here
            summary_fut.result()
            asr_fut.result()
            vlm_fut.result()

    # ── Step 3: Show ASR results ──
    print(f"\n[3/6] ASR Results")
    print(f"  Language: {asr_result['language']}")
    print(f"  Sentences:")
    for s in asr_result["sentences"]:
        print(f"    [{s['start']:>5.1f}s - {s['end']:>5.1f}s] {s['text']}")
    print(f"  Words: {len(asr_result['words'])} total")
    if asr_result["words"]:
        # Show word density per second
        word_counts: dict[int, int] = {}
        for w in asr_result["words"]:
            sec = int(w["start"])
            word_counts[sec] = word_counts.get(sec, 0) + 1
        speaking_secs = [s for s, c in word_counts.items() if c > 0]
        print(f"  Speaking seconds: {len(speaking_secs)}/{int(duration)} ({len(speaking_secs)/duration*100:.0f}%)")

    # ── Step 4: Merge timeline ──
    print(f"\n[4/6] Merging ASR + VLM timeline...")
    with Timer("Timeline merge"):
        timeline = merge_timeline(asr_result, vlm_results)

    print(f"\n  Merged timeline ({len(timeline)} seconds):")
    print(f"  {'t':>4} | {'Energy':>6} | {'Signal':<12} | {'Speech':<30} | {'Action':<40}")
    print(f"  {'-'*4}-+-{'-'*6}-+-{'-'*12}-+-{'-'*30}-+-{'-'*40}")
    for entry in timeline:
        e = entry.get("energy", 0)
        bar = "#" * int(e * 6)
        speech = entry.get("speech", "")[:28]
        action = entry.get("action", "")[:38]
        sig = entry.get("edit_signal", "-")
        print(f"  {entry['t']:>4} | {bar:<6} | {sig:<12} | {speech:<30} | {action:<40}")

    # ── Step 5: Edit plan ──
    print(f"\n[5/6] Generating edit plan (speech-aware)...")
    client = httpx.Client(
        timeout=180.0,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with Timer("Edit plan generation"):
        edit_plan = generate_edit_plan(client, timeline, asr_result, duration)

    print(f"\n{'='*70}")
    print("EDIT PLAN")
    print(f"{'='*70}")
    print(json.dumps(edit_plan, indent=2))

    total_elapsed = time.perf_counter() - total_start

    print(f"\n{'='*70}")
    print("TIMING SUMMARY")
    print(f"  Total wall time:     {total_elapsed:.1f}s")
    print(f"  Fast summary:        {summary_time:.1f}s  ← clarifying agent unblocked here")
    print(f"  Dense frames:        {len(frames)} @ {fps} FPS")
    print(f"  Summary frames:      {len(summary_frames)} @ {SUMMARY_FPS} FPS")
    print(f"  Words transcribed:   {len(asr_result['words'])}")
    print(f"  VLM windows:         {len(vlm_results)}")
    print(f"  Timeline entries:    {len(timeline)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
