"""Research node for phase-2 clarification graph."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from server.config import load_graph_agent_config, load_prompt
from server.graph.artifacts import ResearchEvidence, ResearchFinding, ResearchPack
from server.graph.base import GATE_RESEARCH_DONE, RESEARCH_AGENT, NodeRuntime
from server.graph.nodes.shared import parse_json_content, summaries_to_text
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch

logger = logging.getLogger(__name__)


class ResearchEvidenceOutput(BaseModel):
    source: str = ""
    quote: str = ""
    confidence: float = 0.5


class ResearchFindingOutput(BaseModel):
    claim: str
    evidence: list[Any] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    findings: list[ResearchFindingOutput] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


def _coerce_evidence(raw: Any) -> ResearchEvidenceOutput:
    """Accept evidence as a dict or a plain string."""
    if isinstance(raw, dict):
        return ResearchEvidenceOutput(
            source=str(raw.get("source", "")),
            quote=str(raw.get("quote", "")),
            confidence=float(raw.get("confidence", 0.5)),
        )
    return ResearchEvidenceOutput(source="footage", quote=str(raw)[:300])


class ResearchAgent:
    """Builds evidence-backed research findings from planning context."""

    name = RESEARCH_AGENT
    prompt_file = "graph_research.txt"

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        planning_input = state.artifacts.planning_input
        intent = state.artifacts.intent_brief
        if planning_input is None or intent is None:
            raise RuntimeError("planning_input and intent_brief artifacts are required")

        cfg = _merged_config(runtime.config, load_graph_agent_config(self.name))
        summaries_raw = [s.model_dump() for s in planning_input.summaries]
        prompt_text = load_prompt(self.prompt_file)
        messages = [
            {
                "role": "system",
                "content": (
                    f"{prompt_text}\n\n"
                    "Return strict JSON with keys: findings, unresolved.\n"
                    "Each finding has: claim (string), evidence (array of objects).\n"
                    "Each evidence object has: source (string, e.g. 'Video 1'), "
                    "quote (string, direct quote from summary), confidence (float 0-1).\n"
                    "Example evidence: {\"source\": \"Video 1\", \"quote\": \"person opens door\", \"confidence\": 0.8}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Intent summary: {intent.summary}\n\n"
                    f"Open questions: {intent.open_questions}\n\n"
                    f"Video summaries:\n{summaries_to_text(summaries_raw)}"
                ),
            },
        ]

        pack = await _call_llm_or_fallback(
            runtime,
            agent_name=self.name,
            messages=messages,
            summaries=summaries_raw,
            temperature=float(cfg.get("temperature", 0.1)),
            request_id=planning_input.request_id,
            project_id=state.project_id,
        )

        return StatePatch(
            current_node=self.name,
            gates={GATE_RESEARCH_DONE: True},
            artifact_patch=ArtifactPatch(research_pack=pack),
            decisions=[DecisionRecord(node=self.name, decision="research_pack_ready")],
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
) -> ResearchPack:
    if runtime.tools is None:
        logger.info("ResearchAgent: no tools registry, using deterministic fallback")
        return _fallback_research(summaries)

    try:
        result = await runtime.tools.call(
            agent_name,
            "llm_chat",
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 8192,
                "project_id": project_id,
                "request_id": request_id,
            },
        )
        content = _extract_content(result)
        parsed = ResearchOutput.model_validate(parse_json_content(content))
        return ResearchPack(
            findings=[
                ResearchFinding(
                    claim=f.claim,
                    evidence=[
                        ResearchEvidence(
                            source=e.source,
                            quote=e.quote,
                            confidence=max(0.0, min(1.0, float(e.confidence))),
                        )
                        for e in (_coerce_evidence(raw) for raw in f.evidence)
                    ],
                )
                for f in parsed.findings
            ],
            unresolved=parsed.unresolved,
        )
    except Exception as exc:
        logger.warning("ResearchAgent fallback: %s", exc)
        return _fallback_research(summaries)


def _fallback_research(summaries: list[dict[str, Any]]) -> ResearchPack:
    findings: list[ResearchFinding] = []
    unresolved = ["Preferred final duration", "Preferred editing style"]
    for summary in summaries[:2]:
        text = str(summary.get("summary", ""))[:200]
        findings.append(
            ResearchFinding(
                claim=(
                    f"Video '{summary.get('filename', 'unknown')}' contains "
                    "key narrative context."
                ),
                evidence=[
                    ResearchEvidence(
                        source=str(summary.get("filename", "unknown")),
                        quote=text or "No summary available.",
                        confidence=0.55,
                    )
                ],
            )
        )
    return ResearchPack(findings=findings, unresolved=unresolved)


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
    override = runtime_cfg.get("agents", {}).get(RESEARCH_AGENT, {})
    if isinstance(override, dict):
        merged.update(override)
    return merged
