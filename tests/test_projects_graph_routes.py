from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import server.graph as graph_pkg
import server.routes.projects as projects_module
from server.config import get_settings
from server.main import app
from server.routes import projects as projects_routes


def _seed_project() -> str:
    project_id = "proj_graph_routes"
    projects_routes._projects[project_id] = {
        "id": project_id,
        "status": "ready_for_clarify",
        "videos": [{"id": "vid_1", "filename": "clip.mp4"}],
        "ingestion_data": {
            "vid_1": {
                "duration_s": 15.0,
                "summary": "A person talks to camera and then demonstrates a task.",
                "asr": {"sentences": [{"text": "hello world"}]},
                "timeline": [{"t": 0, "action": "talking"}],
            }
        },
        "structured_prompt": None,
        "output_uri": None,
        "error": None,
    }
    return project_id


def test_questions_uses_graph_when_enabled(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("GRAPH_ENABLED", "true")
    get_settings.cache_clear()
    project_id = _seed_project()

    async def fake_graph(project, request_id=""):  # type: ignore[no-untyped-def]
        assert project["id"] == project_id
        return {
            "analysis": "graph analysis",
            "intro": "graph intro",
            "suggested_storylines": [],
            "questions": [{"id": "video_length", "text": "How long?"}],
        }

    monkeypatch.setattr(graph_pkg, "run_clarification_questions_graph", fake_graph)

    with TestClient(app) as client:
        resp = client.get(f"/api/projects/{project_id}/questions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["analysis"] == "graph analysis"
    assert body["intro"] == "graph intro"


def test_questions_graph_failure_falls_back_to_legacy(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "true")
    get_settings.cache_clear()
    project_id = _seed_project()

    async def fake_graph_fail(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    async def fake_legacy(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {
            "analysis": "legacy analysis",
            "suggested_storylines": [],
            "questions": [{"id": "video_style", "text": "Style?"}],
        }

    monkeypatch.setattr(graph_pkg, "run_clarification_questions_graph", fake_graph_fail)
    import server.agents.clarifying as clarifying_agent

    monkeypatch.setattr(clarifying_agent, "generate_initial_questions", fake_legacy)

    with TestClient(app) as client:
        resp = client.get(f"/api/projects/{project_id}/questions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["analysis"] == "legacy analysis"


def test_clarify_graph_failure_falls_back_to_legacy(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "true")
    get_settings.cache_clear()
    project_id = _seed_project()

    async def fake_graph_fail(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("graph failure")

    async def fake_legacy(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"status": "ready", "structured_prompt": "legacy prompt"}

    monkeypatch.setattr(graph_pkg, "run_user_verification_graph", fake_graph_fail)
    import server.agents.clarifying as clarifying_agent

    monkeypatch.setattr(clarifying_agent, "process_answers", fake_legacy)

    with TestClient(app) as client:
        resp = client.post(
            f"/api/projects/{project_id}/clarify",
            json={"answers": {"video_length": "Short (15-60s)"}},
        )
    assert resp.status_code == 200
    assert resp.json()["structured_prompt"] == "legacy prompt"


def test_clarify_graph_disabled_uses_legacy(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "false")
    get_settings.cache_clear()
    project_id = _seed_project()

    async def fake_graph_fail(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("graph should not run when disabled")

    async def fake_legacy(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"status": "ready", "structured_prompt": "legacy only prompt"}

    monkeypatch.setattr(graph_pkg, "run_user_verification_graph", fake_graph_fail)
    import server.agents.clarifying as clarifying_agent

    monkeypatch.setattr(clarifying_agent, "process_answers", fake_legacy)

    with TestClient(app) as client:
        resp = client.post(
            f"/api/projects/{project_id}/clarify",
            json={"answers": {"video_length": "Short (15-60s)"}},
        )
    assert resp.status_code == 200
    assert resp.json()["structured_prompt"] == "legacy only prompt"


def test_questions_graph_disabled_uses_legacy(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "false")
    get_settings.cache_clear()
    project_id = _seed_project()

    async def fake_graph_fail(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("graph should not run when disabled")

    async def fake_legacy(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {
            "analysis": "legacy only",
            "suggested_storylines": [],
            "questions": [{"id": "video_style", "text": "Style?"}],
        }

    monkeypatch.setattr(graph_pkg, "run_clarification_questions_graph", fake_graph_fail)
    import server.agents.clarifying as clarifying_agent

    monkeypatch.setattr(clarifying_agent, "generate_initial_questions", fake_legacy)

    with TestClient(app) as client:
        resp = client.get(f"/api/projects/{project_id}/questions")
    assert resp.status_code == 200
    assert resp.json()["analysis"] == "legacy only"


def test_run_editing_uses_graph_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "true")
    monkeypatch.setenv("GRAPH_FAIL_OPEN", "true")
    get_settings.cache_clear()

    project_id = "proj_edit_graph"
    projects_module._projects[project_id] = {
        "id": project_id,
        "status": "editing",
        "videos": [],
        "ingestion_data": {},
        "structured_prompt": "keep it short",
        "output_uri": None,
        "error": None,
    }

    async def fake_graph(project):  # type: ignore[no-untyped-def]
        assert project["id"] == project_id
        return {"output_uri": "data/output/graph.mp4"}

    async def fake_legacy(_project):  # type: ignore[no-untyped-def]
        raise RuntimeError("legacy should not run")

    monkeypatch.setattr(graph_pkg, "run_editing_pipeline_graph", fake_graph)
    import server.agents.editing as editing_agent

    monkeypatch.setattr(editing_agent, "run_editing_agent", fake_legacy)

    asyncio.run(projects_module._run_editing(project_id))
    project = projects_module._projects[project_id]
    assert project["status"] == "complete"
    assert project["output_uri"] == "data/output/graph.mp4"


def test_run_editing_graph_failure_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "true")
    monkeypatch.setenv("GRAPH_FAIL_OPEN", "true")
    get_settings.cache_clear()

    project_id = "proj_edit_fallback"
    projects_module._projects[project_id] = {
        "id": project_id,
        "status": "editing",
        "videos": [],
        "ingestion_data": {},
        "structured_prompt": "keep it short",
        "output_uri": None,
        "error": None,
    }

    async def fake_graph_fail(_project):  # type: ignore[no-untyped-def]
        raise RuntimeError("graph fail")

    async def fake_legacy(_project):  # type: ignore[no-untyped-def]
        return "data/output/legacy.mp4"

    monkeypatch.setattr(graph_pkg, "run_editing_pipeline_graph", fake_graph_fail)
    import server.agents.editing as editing_agent

    monkeypatch.setattr(editing_agent, "run_editing_agent", fake_legacy)

    asyncio.run(projects_module._run_editing(project_id))
    project = projects_module._projects[project_id]
    assert project["status"] == "complete"
    assert project["output_uri"] == "data/output/legacy.mp4"


def test_run_editing_graph_failure_fail_closed_sets_error(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "true")
    monkeypatch.setenv("GRAPH_FAIL_OPEN", "false")
    get_settings.cache_clear()

    project_id = "proj_edit_fail_closed"
    projects_module._projects[project_id] = {
        "id": project_id,
        "status": "editing",
        "videos": [],
        "ingestion_data": {},
        "structured_prompt": "keep it short",
        "output_uri": None,
        "error": None,
    }

    async def fake_graph_fail(_project):  # type: ignore[no-untyped-def]
        raise RuntimeError("graph fail closed")

    async def fake_legacy(_project):  # type: ignore[no-untyped-def]
        raise RuntimeError("legacy should not run in fail-closed mode")

    monkeypatch.setattr(graph_pkg, "run_editing_pipeline_graph", fake_graph_fail)
    import server.agents.editing as editing_agent

    monkeypatch.setattr(editing_agent, "run_editing_agent", fake_legacy)

    asyncio.run(projects_module._run_editing(project_id))
    project = projects_module._projects[project_id]
    assert project["status"] == "error"
    assert project["output_uri"] is None
    assert "graph fail closed" in str(project.get("error", ""))


def test_run_editing_graph_disabled_uses_legacy(monkeypatch) -> None:
    monkeypatch.setenv("GRAPH_ENABLED", "false")
    monkeypatch.setenv("GRAPH_FAIL_OPEN", "true")
    get_settings.cache_clear()

    project_id = "proj_edit_legacy_only"
    projects_module._projects[project_id] = {
        "id": project_id,
        "status": "editing",
        "videos": [],
        "ingestion_data": {},
        "structured_prompt": "keep it short",
        "output_uri": None,
        "error": None,
    }

    async def fake_graph(_project):  # type: ignore[no-untyped-def]
        raise RuntimeError("graph should not run when disabled")

    async def fake_legacy(_project):  # type: ignore[no-untyped-def]
        return "data/output/legacy-only.mp4"

    monkeypatch.setattr(graph_pkg, "run_editing_pipeline_graph", fake_graph)
    import server.agents.editing as editing_agent

    monkeypatch.setattr(editing_agent, "run_editing_agent", fake_legacy)

    asyncio.run(projects_module._run_editing(project_id))
    project = projects_module._projects[project_id]
    assert project["status"] == "complete"
    assert project["output_uri"] == "data/output/legacy-only.mp4"
