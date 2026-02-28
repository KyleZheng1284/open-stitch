"""Clarifying Agent — analyzes video summaries, suggests storylines, asks directed questions."""
from __future__ import annotations

import json
import logging

import httpx

from server.config import get_settings

logger = logging.getLogger(__name__)


def _call_llm(messages: list[dict], max_tokens: int = 2048) -> str:
    s = get_settings()
    client = httpx.Client(
        timeout=60.0,
        headers={"Authorization": f"Bearer {s.nvidia_api_key}", "Content-Type": "application/json"},
    )
    payload = {
        "model": s.clarifying_model,
        "messages": messages,
        "temperature": s.clarifying_temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    logger.info("Clarifying LLM call: model=%s", s.clarifying_model)
    resp = client.post(f"{s.nvidia_base_url}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def generate_initial_questions(summaries: list[dict]) -> dict:
    """Analyze video summaries and generate directed clarifying questions.

    The agent reads what's in the videos and suggests possible storylines,
    then asks the user to pick/refine their vision.
    """
    summary_block = "\n\n".join(
        f"Video {i+1} ({s.get('filename', 'unknown')}, {s.get('duration_s', 0):.0f}s):\n{s.get('summary', 'No summary')}"
        for i, s in enumerate(summaries)
    )

    total_duration = sum(s.get("duration_s", 0) for s in summaries)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert video editor and creative director. The user has "
                "uploaded raw footage and you've analyzed it. Your job is to:\n\n"
                "1. UNDERSTAND what's in the footage — identify the key moments, "
                "people, locations, actions, and narrative threads\n"
                "2. SUGGEST 2-3 possible storylines or edit directions based on "
                "what you see (e.g. 'a day-in-the-life vlog focusing on the cooking "
                "scenes', 'a high-energy montage of the outdoor activities')\n"
                "3. ASK directed questions that help you make precise editing decisions\n\n"
                "Your questions should reference SPECIFIC content from the summaries. "
                "Don't ask generic questions like 'what style do you want' — instead "
                "ask things like 'I noticed cooking scenes in Video 1 and a sunset in "
                "Video 2 — should I build the story around the cooking with the sunset "
                "as the ending, or focus on something else?'\n\n"
                f"Total raw footage: {total_duration:.0f}s across {len(summaries)} video(s).\n\n"
                "Return JSON with this exact structure:\n"
                "{\n"
                '  "analysis": "1-2 sentence summary of what you see across all videos",\n'
                '  "suggested_storylines": [\n'
                '    {"title": "short name", "description": "what this edit would look like"}\n'
                "  ],\n"
                '  "questions": [\n'
                '    {"id": "q1", "text": "specific question referencing video content", "options": ["option1", "option2"] or null}\n'
                "  ]\n"
                "}\n\n"
                "Always include these as your last 2 questions:\n"
                "- Target length (with options: 'Short (15-60s)', 'Long (1-5min)')\n"
                "- A free-text question asking the user to describe anything specific "
                "they want included or excluded\n\n"
                "Return ONLY valid JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Here's what I see in the uploaded footage:\n\n{summary_block}\n\n"
                "Analyze this footage and generate your questions."
            ),
        },
    ]

    raw = _call_llm(messages)
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        result = json.loads(clean)
        # Prepend analysis + storylines as the first "message" the user sees
        intro_parts = []
        if result.get("analysis"):
            intro_parts.append(result["analysis"])
        if result.get("suggested_storylines"):
            intro_parts.append("\nHere are some directions I could take this:")
            for i, sl in enumerate(result["suggested_storylines"], 1):
                intro_parts.append(f"  {i}. **{sl['title']}** — {sl['description']}")

        if intro_parts:
            result["intro"] = "\n".join(intro_parts)

        logger.info(
            "Clarifying agent: %d storylines, %d questions",
            len(result.get("suggested_storylines", [])),
            len(result.get("questions", [])),
        )
        return result

    except json.JSONDecodeError:
        logger.error("Failed to parse clarifying JSON: %s", raw[:300])
        return {
            "intro": "I've reviewed your footage. Let me ask a few questions to plan the edit.",
            "questions": [
                {"id": "q1", "text": "How long should the final video be?", "options": ["Short (15-60s)", "Long (1-5min)"]},
                {"id": "q2", "text": "What style are you going for?", "options": ["Vlog", "Tutorial", "Highlights", "Cinematic", "Story"]},
                {"id": "q3", "text": "Describe your vision — what moments should be included?", "options": None},
            ],
        }


async def process_answers(project: dict, answers: dict[str, str]) -> dict:
    """Process user answers and build the structured prompt for the editing agent."""
    ingestion_data = project.get("ingestion_data", {})
    videos = project.get("videos", [])

    summary_block = ""
    video_data_block = ""
    cumulative_offset = 0.0

    for vid in videos:
        vid_id = vid.id if hasattr(vid, "id") else vid.get("id", "")
        data = ingestion_data.get(vid_id, {})
        duration = data.get("duration_s", 0)
        start_ts = cumulative_offset
        end_ts = cumulative_offset + duration

        summary_block += (
            f"Video: {vid.filename if hasattr(vid, 'filename') else vid.get('filename', vid_id)} "
            f"({_fmt_time(start_ts)} - {_fmt_time(end_ts)})\n"
            f"{data.get('summary', 'No summary available')}\n\n"
        )

        asr = data.get("asr", {})
        transcript = " ".join(s.get("text", "") for s in asr.get("sentences", []))
        timeline_preview = json.dumps(data.get("timeline", [])[:10], indent=1)

        video_data_block += (
            f"You are receiving video timestamped {_fmt_time(start_ts)} - {_fmt_time(end_ts)}:\n"
            f"Transcript: {transcript}\n"
            f"Timeline (first 10s): {timeline_preview}\n\n"
        )

        cumulative_offset = end_ts

    answer_text = "\n".join(f"- {k}: {v}" for k, v in answers.items())

    structured_prompt = (
        f"== Full Summary with Timestamps ==\n{summary_block}\n"
        f"== Video Data ==\n{video_data_block}\n"
        f"== End Goal ==\n"
        f"User preferences:\n{answer_text}\n"
    )

    return {
        "status": "ready",
        "structured_prompt": structured_prompt,
    }


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
