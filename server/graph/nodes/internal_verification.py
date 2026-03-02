"""Internal verification node -- deterministic checks + LLM review."""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from server.config import load_prompt
from server.graph.artifacts import VerificationIssue, VerificationReport
from server.graph.base import GATE_INTERNAL_VERIFIED, INTERNAL_VERIFICATION_AGENT, NodeRuntime
from server.graph.nodes.shared import parse_json_content
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch
from server.graph.validators import (
    build_report,
    retry_target_from_report,
    verify_composition_draft,
    verify_edit_spec,
)

logger = logging.getLogger(__name__)


class VerificationOutput(BaseModel):
    passed: bool = False
    issues: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class InternalVerificationAgent:
    """Runs deterministic pre-checks then an LLM review of the composition."""

    name = INTERNAL_VERIFICATION_AGENT
    prompt_file = "graph_internal_verification.txt"

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        deterministic_issues = []
        deterministic_issues.extend(verify_edit_spec(state.artifacts.edit_spec))
        deterministic_issues.extend(verify_composition_draft(state.artifacts.composition_draft))
        deterministic_report = build_report(deterministic_issues)

        if not deterministic_report.passed:
            retry_target = retry_target_from_report(deterministic_report)
            return StatePatch(
                current_node=self.name,
                next_node=retry_target,
                gates={GATE_INTERNAL_VERIFIED: False},
                artifact_patch=ArtifactPatch(verification_report=deterministic_report),
                decisions=[
                    DecisionRecord(
                        node=self.name,
                        decision="internal_verification_failed",
                        detail=retry_target,
                    )
                ],
            )

        if runtime.tools is None:
            return self._pass(deterministic_report)

        try:
            report = await self._llm_review(state, runtime)
        except Exception as exc:
            logger.warning("InternalVerification LLM review failed, using deterministic: %s", exc)
            return self._pass(deterministic_report)

        if report.passed:
            return self._pass(report)

        retry_target = retry_target_from_report(report)
        return StatePatch(
            current_node=self.name,
            next_node=retry_target,
            gates={GATE_INTERNAL_VERIFIED: False},
            artifact_patch=ArtifactPatch(verification_report=report),
            decisions=[
                DecisionRecord(
                    node=self.name,
                    decision="internal_verification_failed",
                    detail=retry_target,
                )
            ],
        )

    async def _llm_review(self, state: GraphState, runtime: NodeRuntime) -> VerificationReport:
        draft = state.artifacts.composition_draft
        composition_summary = ""
        if draft and draft.composition:
            comp = draft.composition
            seqs = comp.get("sequences", [])
            subs = comp.get("subtitles", [])
            audio = comp.get("audio_layers", [])
            composition_summary = (
                f"Clips: {len(seqs)}, Subtitles: {len(subs)}, Audio: {len(audio)}\n"
                f"Composition JSON (first 2000 chars):\n{json.dumps(comp)[:2000]}"
            )

        structured_prompt = ""
        if state.artifacts.structured_prompt:
            structured_prompt = state.artifacts.structured_prompt.structured_prompt or ""

        prompt_text = load_prompt(self.prompt_file)
        messages = [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": (
                    f"User request:\n{structured_prompt[:1000]}\n\n"
                    f"Composition:\n{composition_summary}"
                ),
            },
        ]

        result = await runtime.tools.call(
            self.name,
            "llm_chat",
            {
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 4096,
                "project_id": state.project_id,
                "request_id": "",
            },
        )
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        parsed = VerificationOutput.model_validate(parse_json_content(content))

        issues = [
            VerificationIssue(
                severity=str(i.get("severity", "warning")),
                code=str(i.get("code", "llm_review")),
                message=str(i.get("message", "")),
            )
            for i in parsed.issues
        ]
        return VerificationReport(passed=parsed.passed, issues=issues)

    def _pass(self, report: VerificationReport) -> StatePatch:
        return StatePatch(
            current_node=self.name,
            next_node=None,
            gates={GATE_INTERNAL_VERIFIED: True},
            artifact_patch=ArtifactPatch(verification_report=report),
            decisions=[DecisionRecord(node=self.name, decision="internal_verified")],
        )
