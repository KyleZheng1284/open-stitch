"""Graph state models and pure state transition helpers."""
from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from server.graph.artifacts import (
    AnswerSet,
    ArtifactBundle,
    CompositionDraft,
    EditSpec,
    IntentBrief,
    PlanningInput,
    QuestionSet,
    RenderReadiness,
    ResearchPack,
    StructuredPromptArtifact,
    UserApproval,
    VerificationReport,
)
from server.graph.base import GATE_NAMES

GraphStatus = Literal["idle", "running", "waiting_for_user", "complete", "error"]


class DecisionRecord(BaseModel):
    """Node decision log entry."""

    model_config = ConfigDict(extra="forbid")

    node: str
    decision: str
    detail: str = ""
    ts: float = Field(default_factory=time.time)


class ErrorRecord(BaseModel):
    """Structured graph error record."""

    model_config = ConfigDict(extra="forbid")

    node: str
    message: str
    recoverable: bool = False
    ts: float = Field(default_factory=time.time)


class TraceRecord(BaseModel):
    """Small state-local trace entry for debugging/tests."""

    model_config = ConfigDict(extra="forbid")

    node: str
    event: str
    metadata: dict[str, str] = Field(default_factory=dict)
    ts: float = Field(default_factory=time.time)


class ArtifactPatch(BaseModel):
    """Partial artifact updates produced by a node."""

    model_config = ConfigDict(extra="forbid")

    planning_input: PlanningInput | None = None
    answer_set: AnswerSet | None = None
    intent_brief: IntentBrief | None = None
    research_pack: ResearchPack | None = None
    question_set: QuestionSet | None = None
    user_approval: UserApproval | None = None
    structured_prompt: StructuredPromptArtifact | None = None
    edit_spec: EditSpec | None = None
    composition_draft: CompositionDraft | None = None
    verification_report: VerificationReport | None = None
    render_readiness: RenderReadiness | None = None


class StatePatch(BaseModel):
    """Partial update merged into GraphState."""

    model_config = ConfigDict(extra="forbid")

    status: GraphStatus | None = None
    current_node: str | None = None
    next_node: str | None = None
    gates: dict[str, bool] = Field(default_factory=dict)
    artifact_patch: ArtifactPatch | None = None
    decisions: list[DecisionRecord] = Field(default_factory=list)
    errors: list[ErrorRecord] = Field(default_factory=list)
    trace: list[TraceRecord] = Field(default_factory=list)


class GraphState(BaseModel):
    """Runtime state object for graph execution."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    status: GraphStatus = "idle"
    current_node: str | None = None
    next_node: str | None = None
    gates: dict[str, bool] = Field(default_factory=lambda: {gate: False for gate in GATE_NAMES})
    artifacts: ArtifactBundle = Field(default_factory=ArtifactBundle)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    errors: list[ErrorRecord] = Field(default_factory=list)
    trace: list[TraceRecord] = Field(default_factory=list)
    updated_at: float = Field(default_factory=time.time)


def new_graph_state(project_id: str, *, run_id: str | None = None) -> GraphState:
    """Create a fresh graph state with default gates/artifacts."""
    state = GraphState(project_id=project_id)
    if run_id:
        state.run_id = run_id
    return state


def apply_state_patch(state: GraphState, patch: StatePatch) -> GraphState:
    """Return a new state with patch values merged in."""
    next_state = state.model_copy(deep=True)
    raw = patch.model_dump(exclude_unset=True)

    if "status" in raw and patch.status is not None:
        next_state.status = patch.status
    if "current_node" in raw:
        next_state.current_node = patch.current_node
    if "next_node" in raw:
        next_state.next_node = patch.next_node

    _merge_gates(next_state, patch.gates)
    _merge_artifacts(next_state, patch.artifact_patch)

    if patch.decisions:
        next_state.decisions.extend(patch.decisions)
    if patch.errors:
        next_state.errors.extend(patch.errors)
    if patch.trace:
        next_state.trace.extend(patch.trace)

    next_state.updated_at = time.time()
    return next_state


def set_gate(state: GraphState, gate: str, value: bool = True) -> GraphState:
    """Return a state copy with one gate updated."""
    if gate not in GATE_NAMES:
        raise ValueError(f"Unknown gate: {gate}")
    return apply_state_patch(state, StatePatch(gates={gate: value}))


def gate_is_open(state: GraphState, gate: str) -> bool:
    """Check whether a gate is open in the current state."""
    if gate not in GATE_NAMES:
        raise ValueError(f"Unknown gate: {gate}")
    return bool(state.gates.get(gate, False))


def _merge_gates(state: GraphState, gates: dict[str, bool]) -> None:
    for gate, value in gates.items():
        if gate not in GATE_NAMES:
            raise ValueError(f"Unknown gate: {gate}")
        state.gates[gate] = value


def _merge_artifacts(state: GraphState, artifact_patch: ArtifactPatch | None) -> None:
    if artifact_patch is None:
        return
    for key in artifact_patch.model_fields_set:
        value = getattr(artifact_patch, key)
        setattr(state.artifacts, key, value)
