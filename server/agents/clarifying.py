"""Clarifying Agent — analyzes video summaries, suggests storylines, asks directed questions."""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from server.config import get_settings, load_agents_config

logger = logging.getLogger(__name__)


class Storyline(BaseModel):
    title: str
    description: str


class ClarifyingQuestion(BaseModel):
    id: str
    text: str
    options: list[str] | None = None


class ClarifyingOutput(BaseModel):
    analysis: str
    suggested_storylines: list[Storyline] = Field(default_factory=list)
    questions: list[ClarifyingQuestion] = Field(default_factory=list)


_REQUIRED_QUESTION_TEMPLATES: dict[str, dict[str, Any]] = {
    "video_length": {
        "id": "video_length",
        "text": "How long should the final video be?",
        "options": ["Short (15-60s)", "Long (1-5min)"],
    },
    "video_style": {
        "id": "video_style",
        "text": "What style are you going for?",
        "options": ["Vlog", "Tutorial", "Highlights", "Cinematic", "Story"],
    },
    "include_exclude": {
        "id": "include_exclude",
        "text": "Anything specific you want included or excluded?",
        "options": None,
    },
}


def _retry_delay_s(attempt: int) -> float:
    # Exponential backoff with small jitter to avoid thundering herd retries.
    return min(2.0, (2 ** attempt) * 0.25) + random.uniform(0.0, 0.2)


async def _call_llm(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 2048,
    temperature: float | None = None,
    retries: int = 2,
) -> str:
    s = get_settings()
    use_temp = s.clarifying_temperature if temperature is None else temperature
    payload = {
        "model": s.clarifying_model,
        "messages": messages,
        "temperature": use_temp,
        "max_tokens": max_tokens,
        "stream": False,
    }
    logger.info("Clarifying LLM call: model=%s temp=%.2f", s.clarifying_model, use_temp)

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(
                timeout=60.0,
                headers={
                    "Authorization": f"Bearer {s.nvidia_api_key}",
                    "Content-Type": "application/json",
                },
            ) as client:
                resp = await client.post(f"{s.nvidia_base_url}/chat/completions", json=payload)

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                if attempt < retries:
                    delay = _retry_delay_s(attempt)
                    logger.warning(
                        "Clarifying LLM retrying after status=%d (attempt %d/%d, %.2fs delay)",
                        resp.status_code,
                        attempt + 1,
                        retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            if attempt < retries:
                delay = _retry_delay_s(attempt)
                logger.warning(
                    "Clarifying LLM transport retry (attempt %d/%d, %.2fs delay): %s",
                    attempt + 1,
                    retries + 1,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                continue
            raise

    raise RuntimeError("Clarifying LLM call failed after retries")


def _load_clarifying_config() -> dict[str, Any]:
    cfg = load_agents_config().get("clarifying", {})
    if not isinstance(cfg, dict):
        return {}
    return cfg


def _required_prompt_lines(required_questions: list[str]) -> str:
    lines = []
    for qid in required_questions:
        template = _REQUIRED_QUESTION_TEMPLATES.get(qid)
        if template is None:
            continue
        options = template.get("options")
        if options:
            lines.append(f'- id="{qid}": {template["text"]} Options: {options}.')
        else:
            lines.append(f'- id="{qid}": {template["text"]}')
    return "\n".join(lines)


def _parse_structured_output(raw: str) -> ClarifyingOutput:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return ClarifyingOutput.model_validate_json(clean)


def _enforce_question_rules(
    questions: list[ClarifyingQuestion],
    *,
    required_questions: list[str],
    max_questions: int,
) -> list[dict[str, Any]]:
    by_id: dict[str, ClarifyingQuestion] = {}
    ordered_ids: list[str] = []

    for question in questions:
        if question.id not in by_id:
            ordered_ids.append(question.id)
        by_id[question.id] = question

    for qid in required_questions:
        if qid not in by_id and qid in _REQUIRED_QUESTION_TEMPLATES:
            by_id[qid] = ClarifyingQuestion.model_validate(_REQUIRED_QUESTION_TEMPLATES[qid])
            ordered_ids.append(qid)

    required_set = set(required_questions)
    optional = [qid for qid in ordered_ids if qid not in required_set]
    required_ordered = [qid for qid in required_questions if qid in by_id]
    total_cap = max(max_questions, len(required_ordered))
    optional_budget = max(total_cap - len(required_ordered), 0)
    final_ids = optional[:optional_budget] + required_ordered

    return [by_id[qid].model_dump() for qid in final_ids]


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
    clarifying_cfg = _load_clarifying_config()
    max_questions = int(clarifying_cfg.get("max_questions", 4))
    required_questions = clarifying_cfg.get("required_questions", ["video_length", "video_style"])
    if not isinstance(required_questions, list):
        required_questions = ["video_length", "video_style"]
    required_questions = [str(qid) for qid in required_questions]
    temperature_cfg = clarifying_cfg.get("temperature")
    use_temperature = float(temperature_cfg) if temperature_cfg is not None else None

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
                f"Question count cap: {max_questions} total questions.\n"
                "Required questions that must be included in output (exact IDs):\n"
                f"{_required_prompt_lines(required_questions)}\n\n"
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

    raw = await _call_llm(messages, temperature=use_temperature)
    try:
        parsed = _parse_structured_output(raw)
    except (json.JSONDecodeError, ValidationError, ValueError):
        logger.warning("Clarifying response validation failed; retrying once with stricter prompt")
        fallback_messages = [
            {
                "role": "system",
                "content": (
                    "Return strict JSON only with keys: analysis, suggested_storylines, questions.\n"
                    "analysis must be a string.\n"
                    "suggested_storylines must be a list of {title, description}.\n"
                    "questions must be a list of {id, text, options} where options is array or null.\n"
                    f"Keep total questions <= {max_questions}.\n"
                    "Include required questions with exact IDs:\n"
                    f"{_required_prompt_lines(required_questions)}"
                ),
            },
            {
                "role": "user",
                "content": f"Footage summaries:\n{summary_block}",
            },
        ]
        retry_raw = await _call_llm(
            fallback_messages,
            temperature=use_temperature,
            retries=1,
        )
        try:
            parsed = _parse_structured_output(retry_raw)
        except (json.JSONDecodeError, ValidationError, ValueError):
            logger.error("Failed to parse clarifying JSON after retry")
            return _build_fallback_response(required_questions, max_questions)

    result = parsed.model_dump()
    result["questions"] = _enforce_question_rules(
        parsed.questions,
        required_questions=required_questions,
        max_questions=max_questions,
    )

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


def _build_fallback_response(required_questions: list[str], max_questions: int) -> dict:
    base_questions = [
        _REQUIRED_QUESTION_TEMPLATES["include_exclude"],
    ]
    structured = _enforce_question_rules(
        [ClarifyingQuestion.model_validate(q) for q in base_questions],
        required_questions=required_questions,
        max_questions=max_questions,
    )
    return {
        "intro": "I've reviewed your footage. Let me ask a few questions to plan the edit.",
        "analysis": "I can see enough footage context to start planning your edit direction.",
        "suggested_storylines": [],
        "questions": structured,
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
