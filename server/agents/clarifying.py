"""Clarifying Agent — generates questions from summaries, builds structured prompt."""
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
        "model": s.llm_model,
        "messages": messages,
        "temperature": s.llm_temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = client.post(f"{s.nvidia_base_url}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def generate_initial_questions(summaries: list[dict]) -> dict:
    """Given video summaries, generate clarifying questions for the user.

    Returns: {"questions": [{"id": str, "text": str, "options": [...] | None}], "context": str}
    """
    summary_block = "\n\n".join(
        f"Video {i+1} ({s.get('filename', 'unknown')}, {s.get('duration_s', 0):.0f}s):\n{s.get('summary', 'No summary')}"
        for i, s in enumerate(summaries)
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a video editing assistant. The user has uploaded videos and you need to "
                "understand what kind of final video they want. Generate 2-4 clarifying questions. "
                "Always ask about: (1) intended video length (short 15-60s or long 1-10min), "
                "(2) style/vibe (vlog, tutorial, highlights, cinematic, story). "
                "You may ask about specific moments to include or exclude.\n\n"
                "Return JSON: {\"questions\": [{\"id\": \"q1\", \"text\": \"...\", \"options\": [...] or null}]}"
            ),
        },
        {
            "role": "user",
            "content": f"Here are the video summaries:\n\n{summary_block}\n\nGenerate clarifying questions.",
        },
    ]

    raw = _call_llm(messages)
    # Parse JSON from response
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {
            "questions": [
                {"id": "q1", "text": "How long should the final video be?", "options": ["Short (15-60s)", "Long (1-10min)"]},
                {"id": "q2", "text": "What style of video do you want?", "options": ["Vlog", "Tutorial", "Highlights", "Cinematic", "Story"]},
            ]
        }


async def process_answers(project: dict, answers: dict[str, str]) -> dict:
    """Process user answers and return next questions or the final structured prompt."""
    ingestion_data = project.get("ingestion_data", {})
    videos = project.get("videos", [])

    # Build summary block with timestamps
    summary_block = ""
    video_data_block = ""
    cumulative_offset = 0.0

    for vid in videos:
        vid_id = vid.id if hasattr(vid, "id") else vid.get("id", "")
        data = ingestion_data.get(vid_id, {})
        duration = data.get("duration_s", 0)
        start_ts = cumulative_offset
        end_ts = cumulative_offset + duration

        # Summary section
        summary_block += (
            f"Video: {vid.filename if hasattr(vid, 'filename') else vid.get('filename', vid_id)} "
            f"({_fmt_time(start_ts)} - {_fmt_time(end_ts)})\n"
            f"{data.get('summary', 'No summary available')}\n\n"
        )

        # Detailed video data section
        asr = data.get("asr", {})
        transcript = " ".join(s.get("text", "") for s in asr.get("sentences", []))
        timeline_preview = json.dumps(data.get("timeline", [])[:10], indent=1)

        video_data_block += (
            f"You are receiving video timestamped {_fmt_time(start_ts)} - {_fmt_time(end_ts)}:\n"
            f"Transcript: {transcript}\n"
            f"Timeline (first 10s): {timeline_preview}\n\n"
        )

        cumulative_offset = end_ts

    # Build end goal from answers
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
