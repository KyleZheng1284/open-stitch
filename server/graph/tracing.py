"""Trace adapter for graph node lifecycle events."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from server.events import AgentTracer, emit
from server.graph.events import GRAPH_GATE_EVENT, GRAPH_STATE_EVENT

if TYPE_CHECKING:
    from server.graph.state import GraphState

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GraphTraceAdapter:
    """Maps graph lifecycle events to existing tracing infrastructure."""

    project_id: str
    parent_id: str = "pipeline"
    _tracers: dict[str, AgentTracer] = field(default_factory=dict)

    def node_start(self, node_name: str, *, max_turns: int | None = None) -> None:
        """Emit node-start through AgentTracer for UI compatibility."""
        logger.info("graph.trace.node_start project_id=%s node=%s", self.project_id, node_name)
        tracer = AgentTracer(self.project_id, node_name, parent_id=self.parent_id)
        tracer.on_agent_start(max_turns=max_turns)
        self._tracers[node_name] = tracer

    def node_end(self, node_name: str, *, summary: str = "", error: str | None = None) -> None:
        """Emit node-end through AgentTracer."""
        logger.info(
            "graph.trace.node_end project_id=%s node=%s error=%s",
            self.project_id,
            node_name,
            bool(error),
        )
        tracer = self._tracers.get(node_name)
        if tracer is None:
            tracer = AgentTracer(self.project_id, node_name, parent_id=self.parent_id)
        tracer.on_agent_end(summary=summary, error=error)
        self._tracers.pop(node_name, None)

    def get_tracer(self, node_name: str) -> AgentTracer | None:
        """Return the AgentTracer for a node, if one exists."""
        return self._tracers.get(node_name)

    def gate_decision(self, gate: str, opened: bool, *, reason: str = "") -> None:
        """Emit explicit gate decisions as graph-specific events."""
        emit(
            self.project_id,
            GRAPH_GATE_EVENT,
            node_id=f"gate:{gate}",
            parent_id=self.parent_id,
            gate=gate,
            opened=opened,
            reason=reason,
        )

    def state_snapshot(self, state: GraphState, *, node_name: str) -> None:
        """Emit compact state snapshot metadata for debugging."""
        emit(
            self.project_id,
            GRAPH_STATE_EVENT,
            node_id=f"graph:{node_name}",
            parent_id=self.parent_id,
            status=state.status,
            openGates=sorted([name for name, is_open in state.gates.items() if is_open]),
        )
