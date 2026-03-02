"""Centralized tool registry for graph agents."""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from server.graph.base import AGENT_NAMES

ToolHandler = Callable[[Mapping[str, Any]], Any | Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Tool metadata and handler."""

    name: str
    description: str
    handler: ToolHandler


class ToolRegistry:
    """In-memory tool registry with per-agent allowlists."""

    def __init__(self, allowlists: Mapping[str, set[str]] | None = None):
        self._tools: dict[str, ToolDefinition] = {}
        self._allowlists: dict[str, set[str]] = _normalize_allowlists(allowlists)

    def register(self, definition: ToolDefinition) -> None:
        """Register one tool by unique name."""
        if definition.name in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = definition

    def register_many(self, definitions: list[ToolDefinition]) -> None:
        """Register a list of tools."""
        for definition in definitions:
            self.register(definition)

    def get(self, tool_name: str) -> ToolDefinition:
        """Get tool definition by name."""
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_name}") from exc

    def set_allowlist(self, agent_name: str, tool_names: set[str]) -> None:
        """Set complete allowlist for an agent."""
        self._allowlists[agent_name] = set(tool_names)

    def is_allowed(self, agent_name: str, tool_name: str) -> bool:
        """Check whether agent can call a given tool."""
        return tool_name in self._allowlists.get(agent_name, set())

    def allowlist_for(self, agent_name: str) -> set[str]:
        """Return a copy of the allowlist for one agent."""
        return set(self._allowlists.get(agent_name, set()))

    async def call(self, agent_name: str, tool_name: str, payload: Mapping[str, Any]) -> Any:
        """Call tool if allowlisted for agent."""
        if not self.is_allowed(agent_name, tool_name):
            raise PermissionError(f"Tool '{tool_name}' is not allowed for agent '{agent_name}'")

        definition = self.get(tool_name)
        result = definition.handler(payload)
        if inspect.isawaitable(result):
            return await result
        return result


def default_allowlists() -> dict[str, set[str]]:
    """Default empty allowlists for all known agents."""
    return {agent: set() for agent in AGENT_NAMES}


def default_tool_registry() -> ToolRegistry:
    """Build an empty tool registry with default agent keys."""
    return ToolRegistry(allowlists=default_allowlists())


def _normalize_allowlists(allowlists: Mapping[str, set[str]] | None) -> dict[str, set[str]]:
    normalized = default_allowlists()
    if allowlists is None:
        return normalized
    for agent_name, tool_names in allowlists.items():
        normalized[agent_name] = set(tool_names)
    return normalized
