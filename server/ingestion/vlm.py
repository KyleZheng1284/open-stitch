"""Dense VLM analysis via Gemini 3 Pro."""
from __future__ import annotations

import json
import logging

import httpx

from server.config import api_credentials_for, get_settings

logger = logging.getLogger(__name__)


def _parse_json(content: str) -> dict:
    clean = content.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"raw": content}


def _call(client: httpx.Client, messages: list, model: str, max_tokens: int = 4096) -> str:
    _, base_url = api_credentials_for(model)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = client.post(f"{base_url}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def analyze_window(
    client: httpx.Client,
    frame_uris: list[str],
    window_start_s: float,
    fps: int,
    duration: float,
) -> dict:
    """Analyze a single window of frames."""
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

    s = get_settings()
    raw = _call(client, [{"role": "user", "content": content_parts}], s.vlm_model)
    return _parse_json(raw)


def run_vlm(frame_uris: list[str], fps: int, window_s: int, duration: float, max_concurrent: int = 3) -> list[dict]:
    """Run dense VLM across all windows concurrently. Returns list of window results."""
    from concurrent.futures import ThreadPoolExecutor

    s = get_settings()
    api_key, _ = api_credentials_for(s.vlm_model)
    client = httpx.Client(
        timeout=180.0,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    frames_per_window = fps * window_s
    num_windows = (len(frame_uris) + frames_per_window - 1) // frames_per_window

    def process_window(w: int) -> dict:
        start_idx = w * frames_per_window
        end_idx = min(start_idx + frames_per_window, len(frame_uris))
        window_uris = frame_uris[start_idx:end_idx]
        window_start_s = start_idx / fps
        logger.info("VLM window %d/%d (t=%.1f-%.1fs)", w + 1, num_windows, window_start_s, window_start_s + len(window_uris) / fps)
        return analyze_window(client, window_uris, window_start_s, fps, duration)

    logger.info("Running %d VLM windows (max %d concurrent)", num_windows, max_concurrent)
    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        results = list(pool.map(process_window, range(num_windows)))

    return results
