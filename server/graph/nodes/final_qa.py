"""Final QA node -- LLM-driven last gate before render."""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel

from server.config import load_prompt
from server.graph.artifacts import VerificationIssue, VerificationReport
from server.graph.base import EDITING_SYNTHESIS_AGENT, FINAL_QA_AGENT, GATE_QA_PASSED, NodeRuntime
from server.graph.nodes.shared import parse_json_content
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch

logger = logging.getLogger(__name__)


class QAOutput(BaseModel):
    passed: bool = False
    reason: str = ""


class FinalQAAgent:
    """Final gate before render handoff -- deterministic checks + LLM review."""

    name = FINAL_QA_AGENT
    prompt_file = "graph_final_qa.txt"

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        issues: list[VerificationIssue] = []

        if not state.gates.get("internal_verified", False):
            issues.append(
                VerificationIssue(
                    severity="error",
                    code="qa.internal_not_verified",
                    message="Internal verification gate is not open.",
                )
            )

        draft = state.artifacts.composition_draft
        has_composition = bool(
            draft and draft.composition
            and (draft.composition.get("sequences") or draft.composition.get("image_slides"))
        )
        if not has_composition:
            issues.append(
                VerificationIssue(
                    severity="error",
                    code="qa.composition_missing",
                    message="Final QA requires a non-empty composition.",
                )
            )

        if any(i.severity == "error" for i in issues):
            report = VerificationReport(passed=False, issues=issues)
            return StatePatch(
                current_node=self.name,
                next_node=EDITING_SYNTHESIS_AGENT,
                gates={GATE_QA_PASSED: False},
                artifact_patch=ArtifactPatch(verification_report=report),
                decisions=[DecisionRecord(node=self.name, decision="qa_failed")],
            )

        if runtime.tools is not None and has_composition:
            try:
                llm_passed, llm_reason = await self._llm_check(state, runtime)
                if not llm_passed:
                    issues.append(
                        VerificationIssue(
                            severity="error",
                            code="qa.llm_rejected",
                            message=llm_reason,
                        )
                    )
            except Exception as exc:
                logger.warning("FinalQA LLM check failed, proceeding: %s", exc)

        passed = not any(i.severity == "error" for i in issues)
        report = VerificationReport(passed=passed, issues=issues)

        if passed:
            return StatePatch(
                current_node=self.name,
                next_node=None,
                gates={GATE_QA_PASSED: True},
                artifact_patch=ArtifactPatch(verification_report=report),
                decisions=[DecisionRecord(node=self.name, decision="qa_passed")],
            )

        return StatePatch(
            current_node=self.name,
            next_node=EDITING_SYNTHESIS_AGENT,
            gates={GATE_QA_PASSED: False},
            artifact_patch=ArtifactPatch(verification_report=report),
            decisions=[DecisionRecord(node=self.name, decision="qa_failed")],
        )

    async def _llm_check(self, state: GraphState, runtime: NodeRuntime) -> tuple[bool, str]:
        draft = state.artifacts.composition_draft
        comp = draft.composition if draft else {}
        seqs = comp.get("sequences", []) if isinstance(comp, dict) else []
        subs = comp.get("subtitles", []) if isinstance(comp, dict) else []
        audio = comp.get("audio_layers", []) if isinstance(comp, dict) else []

        structured_prompt = ""
        if state.artifacts.structured_prompt:
            structured_prompt = state.artifacts.structured_prompt.structured_prompt or ""

        prompt_text = load_prompt(self.prompt_file)
        messages = [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": (
                    f"User request (first 500 chars):\n{structured_prompt[:500]}\n\n"
                    f"Composition: {len(seqs)} clips, {len(subs)} subtitles, {len(audio)} audio layers\n"
                    f"Clip details: {json.dumps(seqs[:5])[:500]}"
                ),
            },
        ]

        result = await runtime.tools.call(
            self.name,
            "llm_chat",
            {
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 2048,
                "project_id": state.project_id,
                "request_id": "",
            },
        )
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        parsed = QAOutput.model_validate(parse_json_content(content))
        return parsed.passed, parsed.reason
