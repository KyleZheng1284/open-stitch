from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.graph.artifacts import IntentBrief
from server.graph.base import GATE_PLAN_DONE
from server.graph.state import (
    ArtifactPatch,
    DecisionRecord,
    StatePatch,
    apply_state_patch,
    gate_is_open,
    new_graph_state,
    set_gate,
)


def test_intent_brief_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        IntentBrief(summary="x", unsupported="y")


def test_new_graph_state_defaults() -> None:
    state = new_graph_state("proj_123")
    assert state.project_id == "proj_123"
    assert state.status == "idle"
    assert all(is_open is False for is_open in state.gates.values())


def test_apply_state_patch_merges_without_mutating_original() -> None:
    original = new_graph_state("proj_abc")

    patch = StatePatch(
        status="running",
        current_node="planning",
        gates={GATE_PLAN_DONE: True},
        artifact_patch=ArtifactPatch(
            intent_brief=IntentBrief(
                summary="Plan a short travel montage",
                goals=["keep pace high"],
            ),
        ),
        decisions=[DecisionRecord(node="planning", decision="created_intent_brief")],
    )

    updated = apply_state_patch(original, patch)

    assert original.status == "idle"
    assert updated.status == "running"
    assert updated.current_node == "planning"
    assert gate_is_open(updated, GATE_PLAN_DONE) is True
    assert updated.artifacts.intent_brief is not None
    assert updated.artifacts.intent_brief.summary == "Plan a short travel montage"
    assert len(updated.decisions) == 1


def test_set_gate_rejects_unknown_gate() -> None:
    state = new_graph_state("proj_123")
    with pytest.raises(ValueError, match="Unknown gate"):
        set_gate(state, "not_a_real_gate")
