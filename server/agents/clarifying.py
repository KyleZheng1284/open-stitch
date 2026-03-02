"""Clarifying Agent — analyzes video summaries, suggests storylines, asks directed questions."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import time
import uuid
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from server.config import api_credentials_for, get_settings, load_agents_config

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
    project_id: str | None = None,
    request_id: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
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

    api_key, base_url = api_credentials_for(s.clarifying_model)
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(
                timeout=60.0,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            ) as client:
                resp = await client.post(f"{base_url}/chat/completions", json=payload)

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
            body = resp.json()
            usage = body.get("usage")
            logger.info(
                "Clarifying LLM response project_id=%s request_id=%s latency_ms=%d usage=%s",
                project_id,
                request_id,
                int(resp.elapsed.total_seconds() * 1000),
                usage if isinstance(usage, dict) else None,
            )
            return body["choices"][0]["message"]["content"], usage if isinstance(usage, dict) else None
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


@contextlib.contextmanager
def _clarifying_run_span(project_id: str | None, request_id: str | None):
    start = time.perf_counter()
    logger.info("Clarifying run started project_id=%s request_id=%s", project_id, request_id)
    try:
        yield
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Clarifying run finished project_id=%s request_id=%s latency_ms=%d",
            project_id,
            request_id,
            latency_ms,
        )


def _required_prompt_lines(required_questions: list[str]) -> str:
    lines = []
    for qid in required_questions:
        template = _REQUIRED_QUESTION_TEMPLATES.get(qid)
        if template is None:
            continue
        options = template.get("options")
        if options:
            lines.append(
                f'- id="{qid}" (REQUIRED): covers "{template["text"]}" '
                f"Options: {options}. REWRITE the question text to reference "
                f"specific footage content while keeping these options."
            )
        else:
            lines.append(
                f'- id="{qid}" (REQUIRED): covers "{template["text"]}" '
                f"REWRITE the question text to reference specific footage content."
            )
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


async def generate_initial_questions(
    summaries: list[dict],
    *,
    project_id: str | None = None,
    request_id: str | None = None,
) -> dict:
    """Analyze video summaries and generate directed clarifying questions.

    The agent reads what's in the videos and suggests possible storylines,
    then asks the user to pick/refine their vision.
    """
    req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
    with _clarifying_run_span(project_id, req_id):
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
                    "uploaded raw footage and you've analyzed it.\n\n"
                    "YOUR TASK:\n"
                    "1. ANALYZE what's in the footage — name the key subjects, locations, "
                    "actions, and emotional beats you see\n"
                    "2. SUGGEST 2-3 storylines grounded in the actual footage (reference "
                    "specific videos and scenes)\n"
                    "3. ASK directed questions that reference SPECIFIC content from the "
                    "summaries below\n\n"
                    "CRITICAL RULES:\n"
                    "- NEVER ask a generic question. Every question MUST name a specific "
                    "scene, person, action, or moment from the video summaries.\n"
                    "- For required questions, use the EXACT required IDs but REWRITE the "
                    "question text to reference footage. Example: instead of 'What style "
                    "are you going for?', write 'The door scene in Video 1 has a cinematic "
                    "feel while the outdoor shots in Video 2 are more vlog-style — which "
                    "direction fits your vision?'\n"
                    "- Your analysis must prove you read the summaries: name what you see.\n"
                    "- Storylines must reference specific videos and their content.\n\n"
                    f"Total raw footage: {total_duration:.0f}s across {len(summaries)} video(s).\n"
                    f"Question count cap: {max_questions} total.\n\n"
                    "Required questions (use these exact IDs, rewrite text to reference footage):\n"
                    f"{_required_prompt_lines(required_questions)}\n\n"
                    "Return ONLY valid JSON:\n"
                    "{\n"
                    '  "analysis": "1-3 sentences naming specific content across videos",\n'
                    '  "suggested_storylines": [\n'
                    '    {"title": "name", "description": "grounded description referencing specific footage"}\n'
                    "  ],\n"
                    '  "questions": [\n'
                    '    {"id": "required_id_or_custom", "text": "question referencing specific footage", "options": [...] or null}\n'
                    "  ]\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Here is exactly what I see in each video:\n\n{summary_block}\n\n"
                    "Based on this specific footage, generate your analysis, storylines, "
                    "and questions. Reference the actual content above."
                ),
            },
        ]

        raw, _usage = await _call_llm(
            messages,
            temperature=use_temperature,
            project_id=project_id,
            request_id=req_id,
        )
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
            retry_raw, _retry_usage = await _call_llm(
                fallback_messages,
                temperature=use_temperature,
                retries=1,
                project_id=project_id,
                request_id=req_id,
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
            "Clarifying agent: %d storylines, %d questions project_id=%s request_id=%s",
            len(result.get("suggested_storylines", [])),
            len(result.get("questions", [])),
            project_id,
            req_id,
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
    return {
        "status": "ready",
        "structured_prompt": build_structured_prompt(project, answers),
    }


def extract_video_summaries(project: dict) -> list[dict[str, Any]]:
    """Extract summary payload for each video in a project."""
    ingestion_data = project.get("ingestion_data", {})
    summaries: list[dict[str, Any]] = []
    for vid in project.get("videos", []):
        vid_id = vid.id if hasattr(vid, "id") else vid.get("id", "")
        data = ingestion_data.get(vid_id, {})
        summaries.append({
            "filename": vid.filename if hasattr(vid, "filename") else vid.get("filename", ""),
            "duration_s": data.get("duration_s", 0),
            "summary": data.get("summary", ""),
        })
    return summaries


def build_structured_prompt(project: dict, answers: dict[str, str]) -> str:
    """Build the editing structured prompt from project context + user answers."""
    ingestion_data = project.get("ingestion_data", {})
    videos = project.get("videos", [])

    summary_block = ""
    video_data_block = ""
    cumulative_offset = 0.0

    for vid in videos:
        vid_id = vid.id if hasattr(vid, "id") else vid.get("id", "")
        data = ingestion_data.get(vid_id, {})
        media_type = data.get("media_type", getattr(vid, "media_type", "video"))
        filename = vid.filename if hasattr(vid, "filename") else vid.get("filename", vid_id)

        if media_type == "image":
            summary_block += (
                f"Photo: {filename}\n"
                f"{data.get('summary', 'No description available')}\n\n"
            )
            video_data_block += (
                f"Photo: {filename}\n"
                f"Description: {data.get('summary', '')}\n\n"
            )
        else:
            duration = data.get("duration_s", 0)
            start_ts = cumulative_offset
            end_ts = cumulative_offset + duration

            summary_block += (
                f"Video: {filename} "
                f"({_fmt_time(start_ts)} - {_fmt_time(end_ts)})\n"
                f"{data.get('summary', 'No summary available')}\n\n"
            )

            asr = data.get("asr") or {}
            transcript = " ".join(s.get("text", "") for s in asr.get("sentences", []))
            timeline_preview = json.dumps(data.get("timeline", [])[:10], indent=1)

            video_data_block += (
                f"Video timestamped {_fmt_time(start_ts)} - {_fmt_time(end_ts)}:\n"
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

    return structured_prompt


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
