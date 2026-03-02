from __future__ import annotations

import asyncio

import pytest

from server.graph.graph import LANGGRAPH_AVAILABLE, build_foundation_graph, create_initial_envelope
from server.graph.tools import ToolDefinition, ToolRegistry


def test_tool_registry_allowlist_enforced() -> None:
    async def echo_tool(payload: dict[str, object]) -> dict[str, object]:
        return {"echo": payload["value"]}

    registry = ToolRegistry(allowlists={"planning": {"echo"}})
    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo payload value",
            handler=echo_tool,
        )
    )

    result = asyncio.run(registry.call("planning", "echo", {"value": "ok"}))
    assert result == {"echo": "ok"}

    with pytest.raises(PermissionError, match="not allowed"):
        asyncio.run(registry.call("research", "echo", {"value": "blocked"}))


def test_tool_registry_prevents_duplicate_registration() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(name="noop", description="No-op tool", handler=lambda _: "ok")
    registry.register(definition)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(definition)


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="langgraph not installed in local env")
def test_foundation_graph_pass_through_state() -> None:
    graph = build_foundation_graph()
    envelope = create_initial_envelope("proj_graph")
    result = graph.invoke(envelope)
    assert result["state"].project_id == "proj_graph"
