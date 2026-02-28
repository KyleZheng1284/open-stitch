"""Editing Agent — uses a thinking LLM to produce a precise Remotion edit plan.

The agent receives the full ingestion context (ASR, VLM timeline, summaries)
and user preferences. It calls GPT-5.2 (a reasoning model) which synthesizes
the exact clip selections, subtitle placements, and transition timings that
map 1:1 to Remotion's Composition schema. The output JSON is then converted
directly into a Remotion render call — no guessing, no interpretation.
"""
from __future__ import annotations

import json
import logging

import httpx

from server.config import get_settings
from server.schemas.composition import Composition

logger = logging.getLogger(__name__)

# ── Exact schema the LLM must produce ────────────────────────────────

EDIT_PLAN_SCHEMA = """\
{
  "clips": [
    {
      "source_video": "video_1",
      "start_s": 5.2,
      "end_s": 9.8,
      "speed": 1.0,
      "reason": "why this clip was selected"
    }
  ],
  "subtitles": [
    {
      "text": "exact words from transcript",
      "output_start_s": 0.0,
      "output_end_s": 2.5,
      "style": "tiktok_pop"
    }
  ],
  "transitions": [
    {
      "type": "crossfade",
      "between_clips": [0, 1],
      "duration_ms": 500
    }
  ],
  "music": {"mood": "upbeat", "energy": "high"},
  "title": "short title",
  "total_duration_s": 15.0
}"""


def _call_llm(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 8192,
) -> str:
    """Call any model on the NIM inference API.

    Defaults to editing_model / editing_temperature from config.
    Override with model= and temperature= for other agents.
    """
    s = get_settings()
    use_model = model or s.editing_model
    use_temp = temperature if temperature is not None else s.editing_temperature

    client = httpx.Client(
        timeout=180.0,
        headers={
            "Authorization": f"Bearer {s.nvidia_api_key}",
            "Content-Type": "application/json",
        },
    )
    payload = {
        "model": use_model,
        "messages": messages,
        "temperature": use_temp,
        "max_tokens": max_tokens,
        "stream": False,
    }
    logger.info("LLM call: model=%s temp=%.1f tokens=%d", use_model, use_temp, max_tokens)
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
        logger.error("Failed to parse LLM JSON: %s", content[:500])
        return {"raw": content}


# ── Build video context for the LLM ─────────────────────────────────

def _build_video_context(ingestion_data: dict) -> tuple[str, dict[str, str]]:
    """Build per-video context block and a video_key → file_path lookup.

    Returns (context_text, key_to_path_map).
    """
    context_parts = []
    key_to_path: dict[str, str] = {}

    for i, (vid_id, data) in enumerate(ingestion_data.items()):
        key = f"video_{i + 1}"
        video_path = data.get("video_path", "")
        key_to_path[key] = video_path
        key_to_path[vid_id] = video_path

        duration = data.get("duration_s", 0)
        summary = data.get("summary", "No summary")
        asr = data.get("asr", {})
        transcript = " ".join(s.get("text", "") for s in asr.get("sentences", []))
        timeline = data.get("timeline", [])

        # Compact timeline: only fields the LLM needs for clip selection
        compact = []
        for entry in timeline:
            t = {
                "t": entry.get("t", 0),
                "action": entry.get("action", ""),
                "energy": entry.get("energy", 0),
                "edit_signal": entry.get("edit_signal", "hold"),
                "speech": entry.get("speech", ""),
            }
            if entry.get("subjects"):
                t["subjects"] = entry["subjects"]
            if entry.get("face"):
                t["face"] = entry["face"]
            compact.append(t)

        context_parts.append(
            f"=== {key} ===\n"
            f"Duration: {duration:.1f}s\n"
            f"Summary: {summary}\n"
            f"Transcript: \"{transcript}\"\n"
            f"Per-second timeline ({len(compact)} entries):\n"
            f"{json.dumps(compact, indent=1)}\n"
        )

    return "\n".join(context_parts), key_to_path


# ── Generate edit plan ───────────────────────────────────────────────

def generate_edit_plan(structured_prompt: str, ingestion_data: dict) -> tuple[dict, dict[str, str]]:
    """Call GPT-5.2 with full context to produce a precise edit plan."""
    video_context, key_to_path = _build_video_context(ingestion_data)
    video_keys = sorted(k for k in key_to_path if k.startswith("video_"))
    durations = {}
    for key in video_keys:
        path = key_to_path[key]
        for data in ingestion_data.values():
            if data.get("video_path") == path:
                durations[key] = data.get("duration_s", 0)
                break

    duration_info = ", ".join(f"{k}: {durations.get(k, 0):.1f}s" for k in video_keys)

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Editing Agent for Open-Stitch. Your job is to produce "
                "a precise JSON edit plan that will be executed by Remotion (a React "
                "video renderer). The plan maps directly to render calls — every "
                "field you output becomes a real parameter.\n\n"

                "== WHAT YOU RECEIVE ==\n"
                "1. User preferences: video length, style, specific requests\n"
                "2. Per-video analysis:\n"
                "   - Summary: what happens in the video\n"
                "   - Transcript: exact words spoken (from Whisper ASR)\n"
                "   - Per-second timeline: action description, energy (0-10), "
                "edit_signal (cut/hold), subjects, face expressions\n\n"

                "== WHAT YOU PRODUCE ==\n"
                "A JSON object with this exact schema:\n"
                f"{EDIT_PLAN_SCHEMA}\n\n"

                "== RULES ==\n"
                f"Available source videos: {', '.join(video_keys)}\n"
                f"Video durations: {duration_info}\n\n"
                "1. source_video MUST be one of the listed video keys\n"
                "2. start_s and end_s are timestamps WITHIN that source video "
                "(0 ≤ start_s < end_s ≤ video duration)\n"
                "3. Clips play back-to-back in the output. Clip 0 starts at output "
                "t=0, clip 1 starts when clip 0 ends, etc.\n"
                "4. Subtitles use output_start_s / output_end_s (position in the "
                "FINAL rendered video, not the source). Calculate these from the "
                "cumulative clip durations.\n"
                "5. Use ONLY words from the transcript for subtitles. Do not invent text.\n"
                "6. Pick clips at high-energy moments or where edit_signal='cut'.\n"
                "7. Each clip must have a reason explaining WHY it was selected "
                "based on the timeline data.\n"
                "8. speed: 1.0 = normal, 0.5 = slow-mo, 1.5 = sped up\n"
                "9. transition types: crossfade, cut (instant), fade_to_black\n"
                "10. Return ONLY valid JSON. No markdown, no explanation.\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"== USER REQUEST ==\n{structured_prompt}\n\n"
                f"== VIDEO ANALYSIS ==\n{video_context}\n\n"
                "Think step by step:\n"
                "1. What moments in the timeline match the user's request?\n"
                "2. What are the best start_s/end_s for each clip?\n"
                "3. What transcript words align with those clips for subtitles?\n"
                "4. Calculate output_start_s/output_end_s for subtitles based on "
                "cumulative clip durations.\n\n"
                "Produce the JSON edit plan."
            ),
        },
    ]

    logger.info("Calling editing model (%s) for edit plan...", get_settings().editing_model)
    raw = _call_llm(messages)
    return _parse_json(raw), key_to_path


# ── Build Remotion Composition from edit plan ────────────────────────

def build_composition(edit_plan: dict, key_to_path: dict[str, str], ingestion_data: dict) -> Composition:
    """Convert the LLM's edit plan into a Remotion Composition.

    Maps video_N keys to real file paths and validates timestamps.
    """
    comp = Composition()

    for clip in edit_plan.get("clips", []):
        source_key = clip.get("source_video", "")
        video_path = key_to_path.get(source_key, "")

        if not video_path:
            # Fuzzy match
            for key, path in key_to_path.items():
                if source_key in key or key in source_key:
                    video_path = path
                    break

        if not video_path and key_to_path:
            video_path = next(v for v in key_to_path.values() if v)
            logger.warning("Could not match '%s', defaulting to %s", source_key, video_path)

        start_s = float(clip.get("start_s", 0))
        end_s = float(clip.get("end_s", start_s + 5))

        # Clamp to actual video duration
        for data in ingestion_data.values():
            if data.get("video_path") == video_path:
                max_dur = data.get("duration_s", 9999)
                end_s = min(end_s, max_dur)
                start_s = min(start_s, max_dur - 0.1)
                break

        if end_s <= start_s:
            logger.warning("Skipping invalid clip: start_s=%.1f end_s=%.1f", start_s, end_s)
            continue

        comp.add_sequence(
            source_uri=video_path,
            start_ms=int(start_s * 1000),
            end_ms=int(end_s * 1000),
            speed=float(clip.get("speed", 1.0)),
        )
        logger.info("Clip: %s [%.1fs-%.1fs] speed=%.1fx — %s",
                     source_key, start_s, end_s, clip.get("speed", 1.0), clip.get("reason", ""))

    # Add subtitles (these use output-timeline positions)
    for sub in edit_plan.get("subtitles", []):
        start = sub.get("output_start_s", sub.get("start_s", 0))
        end = sub.get("output_end_s", sub.get("end_s", start + 2))
        comp.add_subtitle(
            text=sub.get("text", ""),
            start_ms=int(float(start) * 1000),
            end_ms=int(float(end) * 1000),
            style=sub.get("style", "tiktok_pop"),
        )

    # Calculate sequence positions (sequential)
    pos = 0
    for seq in comp.sequences:
        seq.position_ms = pos
        pos += int((seq.end_ms - seq.start_ms) / seq.speed)

    if not comp.sequences:
        raise RuntimeError("Edit plan produced no valid clips")

    return comp


# ── Main entry point ─────────────────────────────────────────────────

async def run_editing_agent(project: dict) -> str:
    """Full editing pipeline: plan → composition → render."""
    structured_prompt = project.get("structured_prompt", "")
    ingestion_data = project.get("ingestion_data", {})

    if not ingestion_data:
        raise RuntimeError("No ingestion data — run ingestion first")

    # Step 1: LLM generates edit plan from full video context
    logger.info("Generating edit plan...")
    edit_plan, key_to_path = generate_edit_plan(structured_prompt, ingestion_data)
    logger.info("Edit plan:\n%s", json.dumps(edit_plan, indent=2)[:2000])

    # Step 2: Convert to Remotion Composition
    logger.info("Building composition...")
    composition = build_composition(edit_plan, key_to_path, ingestion_data)
    logger.info("Composition: %d sequences, %d subtitles, %dms total",
                len(composition.sequences), len(composition.subtitles), composition.total_duration_ms)

    # Step 3: Render via sandbox
    logger.info("Rendering via sandbox...")
    from server.sandbox.client import render_composition
    output_uri = await render_composition(composition)

    return output_uri
