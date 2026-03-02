"""Clarification node for phase-2 clarification graph."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from server.config import load_agent_config, load_graph_agent_config, load_prompt
from server.graph.artifacts import ClarifyingQuestion, QuestionSet, Storyline
from server.graph.base import CLARIFICATION_AGENT, NodeRuntime
from server.graph.nodes.shared import parse_json_content, summaries_to_text
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch

logger = logging.getLogger(__name__)

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


class StorylineOutput(BaseModel):
    title: str
    description: str


class ClarifyingQuestionOutput(BaseModel):
    id: str
    text: str
    options: list[str] | None = None


class ClarificationOutput(BaseModel):
    analysis: str
    suggested_storylines: list[StorylineOutput] = Field(default_factory=list)
    questions: list[ClarifyingQuestionOutput] = Field(default_factory=list)


class ClarificationAgent:
    """Produces user-facing questions and storylines from research context."""

    name = CLARIFICATION_AGENT
    prompt_file = "graph_clarification.txt"

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        planning_input = state.artifacts.planning_input
        intent = state.artifacts.intent_brief
        research = state.artifacts.research_pack
        if planning_input is None or intent is None or research is None:
            raise RuntimeError("planning_input, intent_brief, and research_pack are required")

        cfg = _merged_config(runtime.config)
        max_questions = int(cfg.get("max_questions", 4))
        required_questions = cfg.get("required_questions", ["video_length", "video_style"])
        if not isinstance(required_questions, list):
            required_questions = ["video_length", "video_style"]
        required_questions = [str(qid) for qid in required_questions]

        summaries_raw = [s.model_dump() for s in planning_input.summaries]
        prompt_text = load_prompt(self.prompt_file)
        messages = [
            {
                "role": "system",
                "content": (
                    f"{prompt_text}\n\n"
                    f"Question count cap: {max_questions}\n"
                    f"Required question IDs: {required_questions}\n"
                    "Return strict JSON with keys: analysis, suggested_storylines, questions."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Intent summary: {intent.summary}\n\n"
                    f"Open questions: {intent.open_questions}\n\n"
                    f"Research unresolved: {research.unresolved}\n\n"
                    f"Video summaries:\n{summaries_to_text(summaries_raw)}"
                ),
            },
        ]

        question_set = await _call_llm_or_fallback(
            runtime,
            agent_name=self.name,
            messages=messages,
            max_questions=max_questions,
            required_questions=required_questions,
            project_id=state.project_id,
            request_id=planning_input.request_id,
            temperature=float(cfg.get("temperature", 0.2)),
        )

        return StatePatch(
            current_node=self.name,
            artifact_patch=ArtifactPatch(question_set=question_set),
            decisions=[
                DecisionRecord(
                    node=self.name,
                    decision="question_set_ready",
                    detail=str(len(question_set.questions)),
                )
            ],
        )


async def _call_llm_or_fallback(
    runtime: NodeRuntime,
    *,
    agent_name: str,
    messages: list[dict[str, str]],
    max_questions: int,
    required_questions: list[str],
    project_id: str,
    request_id: str,
    temperature: float,
) -> QuestionSet:
    if runtime.tools is None:
        return _fallback_question_set(required_questions, max_questions)

    try:
        result = await runtime.tools.call(
            agent_name,
            "llm_chat",
            {
                "messages": messages,
                "temperature": temperature,
                "project_id": project_id,
                "request_id": request_id,
                "max_tokens": 4096,
            },
        )
        content = _extract_content(result)
        parsed = ClarificationOutput.model_validate(parse_json_content(content))
        questions = _enforce_question_rules(parsed.questions, required_questions, max_questions)
        intro = _build_intro(parsed.analysis, parsed.suggested_storylines)
        return QuestionSet(
            analysis=parsed.analysis,
            intro=intro,
            suggested_storylines=[
                Storyline(title=s.title, description=s.description)
                for s in parsed.suggested_storylines
            ],
            questions=questions,
            max_questions=max_questions,
        )
    except Exception as exc:
        logger.warning("ClarificationAgent fallback: %s", exc)
        return _fallback_question_set(required_questions, max_questions)


def _fallback_question_set(required_questions: list[str], max_questions: int) -> QuestionSet:
    questions = _enforce_question_rules(
        [ClarifyingQuestionOutput(**_REQUIRED_QUESTION_TEMPLATES["include_exclude"])],
        required_questions,
        max_questions,
    )
    analysis = "I can see enough footage context to start planning your edit direction."
    return QuestionSet(
        analysis=analysis,
        intro="I've reviewed your footage. Let me ask a few questions to plan the edit.",
        suggested_storylines=[],
        questions=questions,
        max_questions=max_questions,
    )


def _enforce_question_rules(
    questions: list[ClarifyingQuestionOutput],
    required_questions: list[str],
    max_questions: int,
) -> list[ClarifyingQuestion]:
    by_id: dict[str, ClarifyingQuestionOutput] = {}
    order: list[str] = []
    for question in questions:
        if question.id not in by_id:
            order.append(question.id)
        by_id[question.id] = question

    for qid in required_questions:
        template = _REQUIRED_QUESTION_TEMPLATES.get(qid)
        if qid not in by_id and template is not None:
            by_id[qid] = ClarifyingQuestionOutput(**template)
            order.append(qid)

    required_set = set(required_questions)
    optional_ids = [qid for qid in order if qid not in required_set]
    required_ids = [qid for qid in required_questions if qid in by_id]

    total_cap = max(max_questions, len(required_ids))
    optional_budget = max(total_cap - len(required_ids), 0)
    final_ids = optional_ids[:optional_budget] + required_ids

    return [
        ClarifyingQuestion(
            id=by_id[qid].id,
            text=by_id[qid].text,
            options=by_id[qid].options,
            rationale="",
        )
        for qid in final_ids
    ]


def _build_intro(analysis: str, storylines: list[StorylineOutput]) -> str:
    parts = [analysis] if analysis else []
    if storylines:
        parts.append("\nHere are some directions I could take this:")
        for idx, item in enumerate(storylines, 1):
            parts.append(f"  {idx}. **{item.title}** — {item.description}")
    return "\n".join(parts)


def _extract_content(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        value = result.get("content")
        if isinstance(value, str):
            return value
    raise ValueError("llm_chat tool response must include string 'content'")


def _merged_config(runtime_cfg: dict[str, Any]) -> dict[str, Any]:
    merged = dict(load_agent_config("clarifying"))
    merged.update(load_graph_agent_config(CLARIFICATION_AGENT))
    override = runtime_cfg.get("agents", {}).get(CLARIFICATION_AGENT, {})
    if isinstance(override, dict):
        merged.update(override)
    return merged

