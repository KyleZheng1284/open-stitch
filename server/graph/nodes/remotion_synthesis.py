"""Remotion synthesis node for phase-3 editing graph."""
from __future__ import annotations

from server.graph.artifacts import CompositionDraft
from server.graph.base import REMOTION_SYNTHESIS_AGENT, NodeRuntime
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch


class RemotionSynthesisAgent:
    """Converts edit spec into timeline-oriented draft representation."""

    name = REMOTION_SYNTHESIS_AGENT

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        edit_spec = state.artifacts.edit_spec
        if edit_spec is None:
            raise RuntimeError("edit_spec artifact is required")

        if runtime.tools is not None:
            payload = await runtime.tools.call(
                self.name,
                "edit_spec_to_timeline",
                {"edit_spec": edit_spec.model_dump()},
            )
            timeline = payload.get("timeline", {}) if isinstance(payload, dict) else {}
            warnings = payload.get("warnings", []) if isinstance(payload, dict) else []
        else:
            timeline = {
                "layers": [
                    {
                        "type": "video",
                        "source": clip.source_video,
                        "start_s": clip.start_s,
                        "end_s": clip.end_s,
                    }
                    for clip in edit_spec.clips
                ]
            }
            warnings = []

        draft = state.artifacts.composition_draft or CompositionDraft()
        draft = draft.model_copy(deep=True)
        draft.timeline = timeline if isinstance(timeline, dict) else {}
        draft.warnings = [str(item) for item in warnings]

        return StatePatch(
            current_node=self.name,
            artifact_patch=ArtifactPatch(composition_draft=draft),
            decisions=[DecisionRecord(node=self.name, decision="timeline_ready")],
        )

