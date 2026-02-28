"""Job status and WebSocket streaming."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Shared event bus for progress updates
_subscribers: dict[str, list[asyncio.Queue]] = {}


def publish_event(project_id: str, event: dict):
    """Push event to all WebSocket subscribers for a project."""
    for q in _subscribers.get(project_id, []):
        q.put_nowait(event)


@router.websocket("/{project_id}/stream")
async def job_stream(ws: WebSocket, project_id: str):
    """WebSocket endpoint for real-time pipeline progress."""
    await ws.accept()
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(project_id, []).append(queue)

    try:
        while True:
            event = await queue.get()
            await ws.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers[project_id].remove(queue)
        if not _subscribers[project_id]:
            del _subscribers[project_id]
