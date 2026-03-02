"""Trace event infrastructure -- EventStore + AgentTracer.

EventStore: in-memory per-project event buffer with asyncio.Queue subscriber
notification. Supports replay-from for SSE reconnection.

AgentTracer: generic callback class that any agent instantiates to emit typed
trace events. The frontend renders whatever arrives without hardcoded agent names.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_stores: dict[str, EventStore] = {}


@dataclass
class EventStore:
    """Per-project event buffer with pub-sub via asyncio.Queue."""

    project_id: str
    events: list[dict] = field(default_factory=list)
    _subscribers: list[asyncio.Queue] = field(default_factory=list)

    def emit(self, event_type: str, *, node_id: str, parent_id: str | None = None, **data):
        event = {
            "id": f"evt_{uuid.uuid4().hex[:8]}",
            "type": event_type,
            "ts": time.time(),
            "nodeId": node_id,
            "parentId": parent_id,
            **data,
        }
        self.events.append(event)
        for q in self._subscribers:
            q.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def replay_from(self, last_event_id: str | None) -> list[dict]:
        """Return events after ``last_event_id``, or all events if None."""
        if not last_event_id:
            return list(self.events)
        for i, evt in enumerate(self.events):
            if evt["id"] == last_event_id:
                return self.events[i + 1 :]
        return list(self.events)


def get_store(project_id: str) -> EventStore:
    if project_id not in _stores:
        _stores[project_id] = EventStore(project_id=project_id)
    return _stores[project_id]


def emit(project_id: str, event_type: str, **kwargs):
    """Module-level convenience for non-agent code (ingestion, render)."""
    get_store(project_id).emit(event_type, **kwargs)


# ── AgentTracer ──────────────────────────────────────────────────────


class AgentTracer:
    """Generic tracing callback for any agent.

    Instantiate with a project_id and agent name, then call the lifecycle
    methods from within the agent loop. The frontend trace tree picks up
    events automatically -- no frontend changes needed for new agents.

    Usage::

        tracer = AgentTracer(project_id, "editing")
        tracer.on_agent_start(max_turns=50)
        # per turn:
        tracer.on_llm_start(messages=msgs)
        tracer.on_llm_chunk(token, accumulated)
        tracer.on_llm_end(content=text, tool_calls=tcs)
        tracer.on_tool_start(tc_id, name, args)
        tracer.on_tool_end(tc_id, name, result)
        tracer.on_agent_end(summary="Done")
    """

    def __init__(self, project_id: str, agent_name: str, parent_id: str = "pipeline"):
        self.store = get_store(project_id)
        self.agent_name = agent_name
        self.agent_id = f"agent:{agent_name}"
        self.parent_id = parent_id
        self.turn = 0

    def on_agent_start(self, *, max_turns: int | None = None):
        self.store.emit(
            "agent.start",
            node_id=self.agent_id,
            parent_id=self.parent_id,
            name=self.agent_name,
            maxTurns=max_turns,
        )

    def on_llm_start(self, *, messages: list[dict] | None = None, model: str = ""):
        self.turn += 1
        msg_count = len(messages) if messages else 0
        input_chars = sum(len(m.get("content", "") or "") for m in (messages or []))
        self.store.emit(
            "llm.start",
            node_id=self.agent_id,
            turn=self.turn,
            messageCount=msg_count,
            inputChars=input_chars,
            model=model,
        )

    def on_llm_chunk(self, token: str, accumulated: str):
        self.store.emit(
            "llm.chunk",
            node_id=self.agent_id,
            token=token,
            text=accumulated[-500:],
            turn=self.turn,
        )

    def on_llm_end(
        self,
        *,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        usage: dict | None = None,
    ):
        u = usage or {}
        self.store.emit(
            "llm.end",
            node_id=self.agent_id,
            turn=self.turn,
            hasToolCalls=bool(tool_calls),
            content=(content or "")[:1000],
            toolCallCount=len(tool_calls) if tool_calls else 0,
            promptTokens=u.get("prompt_tokens", 0),
            completionTokens=u.get("completion_tokens", 0),
            totalTokens=u.get("total_tokens", 0),
            outputChars=len(content or ""),
        )

    def on_tool_start(self, tool_call_id: str, name: str, args: dict):
        self.store.emit(
            "tool.start",
            node_id=f"tool:{tool_call_id}",
            parent_id=self.agent_id,
            name=name,
            args=args,
            toolCallId=tool_call_id,
        )

    def on_tool_end(self, tool_call_id: str, name: str, result: str):
        self.store.emit(
            "tool.end",
            node_id=f"tool:{tool_call_id}",
            name=name,
            result=result[:2000],
            toolCallId=tool_call_id,
        )

    def on_agent_end(self, *, summary: str = "", error: str | None = None):
        status = "error" if error else "complete"
        self.store.emit(
            "agent.end",
            node_id=self.agent_id,
            turns=self.turn,
            summary=summary[:500],
            status=status,
            error=error,
        )
