from __future__ import annotations

import asyncio

import pytest

import server.graph.graph as graph_mod
from server.graph.artifacts import CompositionDraft, EditClip, EditSpec
from server.graph.base import GATE_QA_PASSED, SYNTHESIS_AGENT
from server.graph.nodes.internal_verification import InternalVerificationAgent
from server.graph.state import ArtifactPatch, StatePatch, apply_state_patch, new_graph_state
from server.schemas.composition import Composition


def test_internal_verification_routes_back_to_synthesis() -> None:
    state = new_graph_state("proj_loop")
    state = apply_state_patch(
        state,
        StatePatch(
            artifact_patch=ArtifactPatch(
                edit_spec=EditSpec(
                    narrative="bad",
                    clips=[
                        EditClip(
                            source_video="video_1",
                            start_s=1.0,
                            end_s=0.5,
                            reason="invalid range",
                        )
                    ],
                ),
                composition_draft=CompositionDraft(timeline={}, composition={}),
            )
        ),
    )

    patch = asyncio.run(InternalVerificationAgent().run(state, runtime=graph_mod.NodeRuntime()))
    assert patch.next_node == SYNTHESIS_AGENT
    assert patch.gates.get("internal_verified") is False
    assert patch.artifact_patch is not None
    report = patch.artifact_patch.verification_report
    assert report is not None
    assert report.passed is False
    assert any(issue.code.startswith("edit_spec.") for issue in report.issues)


def test_run_editing_pipeline_graph_successful_render_handoff(monkeypatch) -> None:
    project = {"id": "proj_render_ok", "structured_prompt": "Create a short edit."}
    composition = Composition()
    composition.add_sequence(
        source_uri="data/uploads/proj_render_ok/clip.mp4",
        start_ms=0,
        end_ms=1000,
        position_ms=0,
        speed=1.0,
    )

    final_state = new_graph_state(project["id"])
    final_state = apply_state_patch(
        final_state,
        StatePatch(
            gates={GATE_QA_PASSED: True},
            artifact_patch=ArtifactPatch(
                composition_draft=CompositionDraft(
                    timeline={"layers": [{"type": "video"}]},
                    composition=composition.model_dump(),
                )
            ),
        ),
    )

    class FakeGraph:
        async def ainvoke(self, _envelope, config=None):  # type: ignore[no-untyped-def]
            assert config is not None
            return {"state": final_state}

    monkeypatch.setattr(graph_mod, "LANGGRAPH_AVAILABLE", True)
    monkeypatch.setattr(graph_mod, "StateGraph", object())
    def fake_runtime(project_arg, *, trace):  # type: ignore[no-untyped-def]
        _ = trace
        return graph_mod.NodeRuntime(config={"project": project_arg})

    def fake_graph(runtime_arg, trace_arg):  # type: ignore[no-untyped-def]
        _ = runtime_arg, trace_arg
        return FakeGraph()

    monkeypatch.setattr(graph_mod, "_build_runtime", fake_runtime)
    monkeypatch.setattr(graph_mod, "_build_editing_graph", fake_graph)

    called = {"value": False}

    async def fake_render(comp, project_id=None):  # type: ignore[no-untyped-def]
        called["value"] = True
        assert project_id == project["id"]
        assert len(comp.sequences) == 1
        return "data/output/final.mp4"

    import server.sandbox.client as sandbox_client

    monkeypatch.setattr(sandbox_client, "render_composition", fake_render)
    result = asyncio.run(graph_mod.run_editing_pipeline_graph(project))
    assert called["value"] is True
    assert result["output_uri"] == "data/output/final.mp4"


def test_run_editing_pipeline_graph_blocks_render_without_qa(monkeypatch) -> None:
    project = {"id": "proj_render_block", "structured_prompt": "Create a short edit."}
    final_state = new_graph_state(project["id"])
    final_state = apply_state_patch(
        final_state,
        StatePatch(
            gates={GATE_QA_PASSED: False},
            artifact_patch=ArtifactPatch(
                composition_draft=CompositionDraft(
                    timeline={"layers": [{"type": "video"}]},
                    composition={"sequences": [{}]},
                )
            ),
        ),
    )

    class FakeGraph:
        async def ainvoke(self, _envelope, config=None):  # type: ignore[no-untyped-def]
            return {"state": final_state}

    monkeypatch.setattr(graph_mod, "LANGGRAPH_AVAILABLE", True)
    monkeypatch.setattr(graph_mod, "StateGraph", object())
    def fake_runtime(project_arg, *, trace):  # type: ignore[no-untyped-def]
        _ = trace
        return graph_mod.NodeRuntime(config={"project": project_arg})

    def fake_graph(runtime_arg, trace_arg):  # type: ignore[no-untyped-def]
        _ = runtime_arg, trace_arg
        return FakeGraph()

    monkeypatch.setattr(graph_mod, "_build_runtime", fake_runtime)
    monkeypatch.setattr(graph_mod, "_build_editing_graph", fake_graph)

    called = {"value": False}

    async def fake_render(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        called["value"] = True
        return "data/output/should_not_happen.mp4"

    import server.sandbox.client as sandbox_client

    monkeypatch.setattr(sandbox_client, "render_composition", fake_render)

    with pytest.raises(RuntimeError, match="qa_passed"):
        asyncio.run(graph_mod.run_editing_pipeline_graph(project))
    assert called["value"] is False
