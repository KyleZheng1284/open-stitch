"""Synthesis node for phase-3 editing graph -- LLM-driven clip planning."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from server.agents.editing import _build_video_context
from server.agents.tools import plan_clip_specs
from server.config import load_prompt
from server.graph.artifacts import EditClip, EditSpec
from server.graph.base import SYNTHESIS_AGENT, NodeRuntime
from server.graph.nodes.shared import parse_json_content
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch

logger = logging.getLogger(__name__)


class SynthesisOutput(BaseModel):
    narrative: str = ""
    clips: list[dict[str, Any]] = Field(default_factory=list)


class SynthesisAgent:
    """Analyzes video context + user intent via LLM to produce an edit spec."""

    name = SYNTHESIS_AGENT
    prompt_file = "graph_synthesis.txt"

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        project = runtime.config.get("project", {})
        ingestion_data = project.get("ingestion_data", {})
        structured_prompt = str(project.get("structured_prompt", ""))

        if not ingestion_data or runtime.tools is None:
            return self._fallback(project, state)

        video_context, _, durations = _build_video_context(ingestion_data)
        duration_info = ", ".join(
            f"{k}: {v:.1f}s" for k, v in sorted(durations.items())
        )

        prompt_text = load_prompt(self.prompt_file)
        messages = [
            {
                "role": "system",
                "content": (
                    f"{prompt_text}\n\n"
                    f"Available videos: {duration_info}\n"
                    "Return strict JSON with keys: narrative, clips."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User request:\n{structured_prompt}\n\n"
                    f"Video analysis:\n{video_context}"
                ),
            },
        ]

        try:
            result = await runtime.tools.call(
                self.name,
                "llm_chat",
                {
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 8192,
                    "project_id": state.project_id,
                    "request_id": "",
                },
            )
            content = result.get("content", "") if isinstance(result, dict) else str(result)
            parsed = SynthesisOutput.model_validate(parse_json_content(content))
        except Exception as exc:
            logger.warning("SynthesisAgent LLM failed, using deterministic fallback: %s", exc)
            return self._fallback(project, state)

        edit_spec = EditSpec(
            narrative=parsed.narrative or structured_prompt,
            clips=[
                EditClip(
                    source_video=str(c.get("source_video", "")),
                    start_s=float(c.get("start_s", 0.0)),
                    end_s=float(c.get("end_s", 0.0)),
                    reason=str(c.get("reason", "")),
                )
                for c in parsed.clips
            ],
        )

        return StatePatch(
            current_node=self.name,
            artifact_patch=ArtifactPatch(edit_spec=edit_spec),
            decisions=[
                DecisionRecord(
                    node=self.name,
                    decision="edit_spec_ready",
                    detail=f"{len(edit_spec.clips)} clips via LLM",
                )
            ],
        )

    def _fallback(self, project: dict, state: GraphState) -> StatePatch:
        previous_failure = bool(
            state.artifacts.verification_report
            and not state.artifacts.verification_report.passed
        )
        clip_specs = plan_clip_specs(project, previous_failure=previous_failure)
        edit_spec = EditSpec(
            narrative=str(project.get("structured_prompt", "")),
            clips=[
                EditClip(
                    source_video=str(c.get("source_video", "")),
                    start_s=float(c.get("start_s", 0.0)),
                    end_s=float(c.get("end_s", 0.0)),
                    reason=str(c.get("reason", "")),
                )
                for c in clip_specs
            ],
        )
        return StatePatch(
            current_node=self.name,
            artifact_patch=ArtifactPatch(edit_spec=edit_spec),
            decisions=[
                DecisionRecord(
                    node=self.name,
                    decision="edit_spec_ready",
                    detail=f"{len(edit_spec.clips)} clips (fallback)",
                )
            ],
        )
