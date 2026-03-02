"""Flash Lite fast summary — single VLM call at 2 FPS."""
from __future__ import annotations

import logging

import httpx

from server.config import api_credentials_for, get_settings

logger = logging.getLogger(__name__)


def run_fast_summary(frame_uris: list[str], duration: float) -> str:
    """Single-call video summary on Flash Lite. Returns paragraph."""
    s = get_settings()
    api_key, base_url = api_credentials_for(s.summary_model)
    client = httpx.Client(
        timeout=120.0,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )

    content_parts: list[dict] = [
        {"type": "text", "text": (
            f"These are {len(frame_uris)} frames sampled at {s.summary_fps} FPS from a "
            f"{duration:.0f}-second video.\n\n"
            "Write a concise 1-paragraph summary of what happens in this video. "
            "Include: who/what is in it, key actions/events in order, "
            "the setting/location, and the overall mood/vibe. "
            "Be specific about timing (beginning, middle, end)."
        )},
    ]
    for i, uri in enumerate(frame_uris):
        t = i / s.summary_fps
        content_parts.append({"type": "text", "text": f"[t={t:.1f}s]"})
        content_parts.append({"type": "image_url", "image_url": {"url": uri}})

    payload = {
        "model": s.summary_model,
        "messages": [{"role": "user", "content": content_parts}],
        "temperature": 0.3,
        "max_tokens": 512,
        "stream": False,
    }
    resp = client.post(f"{base_url}/chat/completions", json=payload)
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    logger.info("Summary generated: %d chars", len(text))
    return text


def run_image_summary(image_uri: str) -> str:
    """Describe a single image for the editing agent."""
    s = get_settings()
    api_key, base_url = api_credentials_for(s.summary_model)
    client = httpx.Client(
        timeout=60.0,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )

    payload = {
        "model": s.summary_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Describe this photo in detail for a video editor. Include: "
                    "subjects, setting/location, colors, mood, composition, "
                    "and any text visible. Be concise but specific."
                )},
                {"type": "image_url", "image_url": {"url": image_uri}},
            ],
        }],
        "temperature": 0.3,
        "max_tokens": 256,
        "stream": False,
    }
    resp = client.post(f"{base_url}/chat/completions", json=payload)
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    logger.info("Image summary generated: %d chars", len(text))
    return text
