"""Shared constants and interfaces for the graph orchestration layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from server.graph.state import GraphState, StatePatch

PLANNING_AGENT = "planning"
RESEARCH_AGENT = "research"
CLARIFICATION_AGENT = "clarification"
USER_VERIFICATION_AGENT = "user_verification"
INTERNAL_VERIFICATION_AGENT = "internal_verification"
SYNTHESIS_AGENT = "synthesis"
REMOTION_SYNTHESIS_AGENT = "remotion_synthesis"
EDITING_SYNTHESIS_AGENT = "editing_synthesis"
FINAL_QA_AGENT = "final_qa"

AGENT_NAMES: tuple[str, ...] = (
    PLANNING_AGENT,
    RESEARCH_AGENT,
    CLARIFICATION_AGENT,
    USER_VERIFICATION_AGENT,
    INTERNAL_VERIFICATION_AGENT,
    SYNTHESIS_AGENT,
    REMOTION_SYNTHESIS_AGENT,
    EDITING_SYNTHESIS_AGENT,
    FINAL_QA_AGENT,
)

GATE_PLAN_DONE = "plan_done"
GATE_RESEARCH_DONE = "research_done"
GATE_USER_VERIFIED = "user_verified"
GATE_INTERNAL_VERIFIED = "internal_verified"
GATE_SYNTHESIS_DONE = "synthesis_done"
GATE_QA_PASSED = "qa_passed"

GATE_NAMES: tuple[str, ...] = (
    GATE_PLAN_DONE,
    GATE_RESEARCH_DONE,
    GATE_USER_VERIFIED,
    GATE_INTERNAL_VERIFIED,
    GATE_SYNTHESIS_DONE,
    GATE_QA_PASSED,
)


@dataclass
class NodeRuntime:
    """Dependencies that each graph node can use at execution time."""

    config: dict[str, Any] = field(default_factory=dict)
    tools: Any | None = None
    tracer: Any | None = None
    _node_tracer: Any | None = field(default=None, repr=False)


class GraphNode(Protocol):
    """Protocol implemented by node workers used in the graph."""

    name: str

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        """Run node logic and return a state patch."""
        ...
