"""Planning node for the phase-2 clarification graph."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from server.config import load_graph_agent_config, load_prompt
from server.graph.artifacts import IntentBrief
from server.graph.base import GATE_PLAN_DONE, PLANNING_AGENT, NodeRuntime
from server.graph.nodes.shared import parse_json_content, summaries_to_text
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch

logger = logging.getLogger(__name__)


class PlanningOutput(BaseModel):
    summary: str
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class PlanningAgent:
    """Builds an intent brief from summarized footage context."""

    name = PLANNING_AGENT
    prompt_file = "graph_planning.txt"

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        planning_input = state.artifacts.planning_input
        if planning_input is None:
            raise RuntimeError("planning_input artifact is required")

        cfg = _merged_config(runtime.config, load_graph_agent_config(self.name))
        summaries_raw = [s.model_dump() for s in planning_input.summaries]
        summary_block = summaries_to_text(summaries_raw)
        prompt_text = load_prompt(self.prompt_file)
        required = (
            "Return strict JSON with keys: summary, goals, constraints, open_questions. "
            "Each key must be present."
        )
        messages = [
            {"role": "system", "content": f"{prompt_text}\n\n{required}"},
            {"role": "user", "content": summary_block},
        ]

        intent = await _call_llm_or_fallback(
            runtime,
            agent_name=self.name,
            messages=messages,
            summaries=summaries_raw,
            temperature=float(cfg.get("temperature", 0.2)),
            request_id=planning_input.request_id,
            project_id=state.project_id,
        )

        return StatePatch(
            current_node=self.name,
            gates={GATE_PLAN_DONE: True},
            artifact_patch=ArtifactPatch(intent_brief=intent),
            decisions=[DecisionRecord(node=self.name, decision="intent_brief_ready")],
        )


async def _call_llm_or_fallback(
    runtime: NodeRuntime,
    *,
    agent_name: str,
    messages: list[dict[str, str]],
    summaries: list[dict[str, Any]],
    temperature: float,
    request_id: str,
    project_id: str,
) -> IntentBrief:
    if runtime.tools is None:
        logger.info("PlanningAgent: no tools registry, using deterministic fallback")
        return _fallback_intent(summaries)

    try:
        result = await runtime.tools.call(
            agent_name,
            "llm_chat",
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 4096,
                "project_id": project_id,
                "request_id": request_id,
            },
        )
        content = _extract_content(result)
        parsed = PlanningOutput.model_validate(parse_json_content(content))
        return IntentBrief(
            summary=parsed.summary,
            goals=parsed.goals,
            constraints=parsed.constraints,
            open_questions=parsed.open_questions,
        )
    except Exception as exc:
        logger.warning("PlanningAgent fallback: %s", exc)
        return _fallback_intent(summaries)


def _fallback_intent(summaries: list[dict[str, Any]]) -> IntentBrief:
    goals = ["Create a coherent edit that preserves the strongest moments."]
    if summaries:
        goals.append("Keep pacing aligned with the visible activity changes.")
    return IntentBrief(
        summary="Build a clear narrative from the uploaded footage.",
        goals=goals,
        constraints=["Use only supplied footage and inferred timeline context."],
        open_questions=["How long should the final edit be?"],
    )


def _extract_content(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        value = result.get("content")
        if isinstance(value, str):
            return value
    raise ValueError("llm_chat tool response must include string 'content'")


def _merged_config(runtime_cfg: dict[str, Any], file_cfg: dict[str, Any]) -> dict[str, Any]:
    merged = dict(file_cfg)
    override = runtime_cfg.get("agents", {}).get(PLANNING_AGENT, {})
    if isinstance(override, dict):
        merged.update(override)
    return merged

