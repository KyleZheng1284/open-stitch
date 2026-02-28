"""Job management REST + WebSocket endpoints.

Handles job status queries and real-time streaming of agent execution
progress via WebSocket.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Get job status including current phase, step, and ReAct iteration."""
    # TODO: Query job status from database/Redis
    return {
        "job_id": job_id,
        "status": "processing",
        "phase": "react_loop",
        "step": "think",
        "react_iteration": 1,
        "progress": 0.0,
    }


@router.websocket("/jobs/{job_id}/stream")
async def job_stream(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time agent step updates.

    Events emitted:
    - project:ingestion_progress
    - job:status
    - job:react_iteration
    - job:agent_log
    - job:clip_ready
    - job:complete
    - job:error
    """
    await websocket.accept()
    logger.info("WebSocket connected for job %s", job_id)
    try:
        # TODO: Subscribe to Redis pub/sub channel for this job
        # TODO: Forward events to WebSocket client
        while True:
            # Placeholder: wait for client messages or send updates
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for job %s", job_id)
