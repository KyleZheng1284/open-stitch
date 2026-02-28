"""Editing Agent — creates edit plan from structured prompt, implements via Remotion."""
from __future__ import annotations

import json
import logging

import httpx

from server.config import get_settings
from server.schemas.composition import Composition

logger = logging.getLogger(__name__)


def _call_llm(messages: list[dict], max_tokens: int = 8192) -> str:
    s = get_settings()
    client = httpx.Client(
        timeout=180.0,
        headers={"Authorization": f"Bearer {s.nvidia_api_key}", "Content-Type": "application/json"},
    )
    payload = {
        "model": s.llm_model,
        "messages": messages,
        "temperature": s.llm_temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = client.post(f"{s.nvidia_base_url}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _parse_json(content: str) -> dict:
    clean = content.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"raw": content}


def generate_edit_plan(structured_prompt: str, ingestion_data: dict) -> dict:
    """Send structured prompt to Gemini, get JSON edit plan."""
    # Build full timeline from all videos
    full_timeline = []
    for vid_id, data in ingestion_data.items():
        for entry in data.get("timeline", []):
            full_timeline.append(entry)

    asr_sentences = []
    for vid_id, data in ingestion_data.items():
        for s in data.get("asr", {}).get("sentences", []):
            asr_sentences.append(s)

    full_transcript = " ".join(s.get("text", "") for s in asr_sentences)

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Editing Agent for Open-Stitch, an AI video editor. "
                "You receive a structured prompt with video summaries, dense analysis, "
                "and user preferences. Produce a detailed JSON edit plan.\n\n"
                "The edit plan should include:\n"
                "- clips: [{source_video, start_s, end_s, speed, reason}]\n"
                "- transitions: [{type, between, duration_ms}]\n"
                "- subtitles: [{start_s, end_s, text, style}]\n"
                "- music: {mood, energy, genre}\n"
                "- title: catchy title\n"
                "- vibe: 3-5 word aesthetic\n\n"
                "Use ACTUAL transcript words for subtitles. Align edits with speech and visual moments."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{structured_prompt}\n\n"
                f"Full transcript: \"{full_transcript}\"\n\n"
                f"Per-second timeline:\n{json.dumps(full_timeline[:50], indent=1)}\n\n"
                "Produce the JSON edit plan. Return ONLY valid JSON."
            ),
        },
    ]

    raw = _call_llm(messages)
    return _parse_json(raw)


def build_composition(edit_plan: dict, ingestion_data: dict) -> Composition:
    """Convert edit plan into a Remotion Composition."""
    comp = Composition()

    # Add video sequences from clips
    for clip in edit_plan.get("clips", []):
        source = clip.get("source_video", "")
        # Find the actual video path
        video_path = ""
        for vid_id, data in ingestion_data.items():
            if source in (vid_id, data.get("video_path", "")):
                video_path = data["video_path"]
                break
        if not video_path and ingestion_data:
            # Default to first video if source not matched
            video_path = next(iter(ingestion_data.values()))["video_path"]

        comp.add_sequence(
            source_uri=video_path,
            start_ms=int(clip.get("start_s", 0) * 1000),
            end_ms=int(clip.get("end_s", 10) * 1000),
            speed=clip.get("speed", 1.0),
        )

    # Add subtitles
    for sub in edit_plan.get("subtitles", []):
        comp.add_subtitle(
            text=sub.get("text", ""),
            start_ms=int(sub.get("start_s", 0) * 1000),
            end_ms=int(sub.get("end_s", 1) * 1000),
            style=sub.get("style", "tiktok_pop"),
        )

    # Calculate sequence positions (sequential)
    pos = 0
    for seq in comp.sequences:
        seq.position_ms = pos
        pos += int((seq.end_ms - seq.start_ms) / seq.speed)

    return comp


async def run_editing_agent(project: dict) -> str:
    """Full editing pipeline: plan → composition → render.

    Returns output video URI.
    """
    structured_prompt = project.get("structured_prompt", "")
    ingestion_data = project.get("ingestion_data", {})

    # Step 1: Generate edit plan
    logger.info("Generating edit plan...")
    edit_plan = generate_edit_plan(structured_prompt, ingestion_data)
    logger.info("Edit plan: %s", json.dumps(edit_plan, indent=2)[:500])

    # Step 2: Build Remotion composition
    logger.info("Building composition...")
    composition = build_composition(edit_plan, ingestion_data)
    logger.info("Composition: %d sequences, %d subtitles, %dms total",
                len(composition.sequences), len(composition.subtitles), composition.total_duration_ms)

    # Step 3: Render via sandbox
    logger.info("Rendering via sandbox...")
    from server.sandbox.client import render_composition
    output_uri = await render_composition(composition)

    return output_uri
