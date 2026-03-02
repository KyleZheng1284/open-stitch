"""Editing synthesis node -- runs the multi-turn tool-calling editing agent."""
from __future__ import annotations

import logging

from server.events import AgentTracer
from server.graph.artifacts import CompositionDraft
from server.graph.base import EDITING_SYNTHESIS_AGENT, GATE_SYNTHESIS_DONE, NodeRuntime
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch

logger = logging.getLogger(__name__)


class EditingSynthesisAgent:
    """Builds a full composition via the multi-turn tool-calling editing agent."""

    name = EDITING_SYNTHESIS_AGENT

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        project = runtime.config.get("project", {})
        if not project:
            raise RuntimeError("project is required in runtime config")

        tracer: AgentTracer | None = None
        if runtime.tracer is not None:
            tracer = AgentTracer(
                state.project_id,
                self.name,
                parent_id="pipeline",
            )

        from server.agents.editing import build_composition

        composition = await build_composition(project, tracer=tracer)

        draft = state.artifacts.composition_draft or CompositionDraft()
        draft = draft.model_copy(deep=True)
        draft.composition = composition.model_dump()

        return StatePatch(
            current_node=self.name,
            gates={GATE_SYNTHESIS_DONE: True},
            artifact_patch=ArtifactPatch(composition_draft=draft),
            decisions=[
                DecisionRecord(
                    node=self.name,
                    decision="composition_ready",
                    detail=(
                        f"{len(composition.sequences)} clips, "
                        f"{len(composition.subtitles)} subs, "
                        f"{len(composition.audio_layers)} audio"
                    ),
                )
            ],
        )
