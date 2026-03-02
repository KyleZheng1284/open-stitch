"""Job status -- SSE trace stream + legacy WebSocket + dev demo."""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse

from server.events import get_store, emit, AgentTracer

router = APIRouter()


# ── SSE trace stream (primary) ───────────────────────────────────────

@router.get("/{project_id}/events")
async def event_stream(request: Request, project_id: str):
    """SSE endpoint — replays stored events then streams live ones.

    Supports ``Last-Event-ID`` header for seamless reconnection.
    """
    store = get_store(project_id)
    last_id = request.headers.get("last-event-id")

    async def generate():
        for evt in store.replay_from(last_id):
            yield f"id: {evt['id']}\nevent: {evt['type']}\ndata: {json.dumps(evt)}\n\n"

        queue = store.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"id: {evt['id']}\nevent: {evt['type']}\ndata: {json.dumps(evt)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            store.unsubscribe(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Legacy WebSocket (kept for future bidirectional use) ─────────────

_ws_subscribers: dict[str, list[asyncio.Queue]] = {}


def publish_event(project_id: str, event: dict):
    """Push event to all WebSocket subscribers for a project."""
    for q in _ws_subscribers.get(project_id, []):
        q.put_nowait(event)


@router.websocket("/{project_id}/stream")
async def job_stream(ws: WebSocket, project_id: str):
    """WebSocket endpoint for real-time pipeline progress."""
    await ws.accept()
    queue: asyncio.Queue = asyncio.Queue()
    _ws_subscribers.setdefault(project_id, []).append(queue)

    try:
        while True:
            event = await queue.get()
            await ws.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    finally:
        _ws_subscribers[project_id].remove(queue)
        if not _ws_subscribers[project_id]:
            del _ws_subscribers[project_id]


# ── Dev demo: simulate a full pipeline with fake events ──────────────

@router.post("/{project_id}/demo")
async def run_demo(project_id: str):
    """Fire a sequence of mock trace events to preview the trace tree.

    Usage:  curl -X POST http://localhost:8080/api/jobs/demo_123/demo
    Then open: http://localhost:5173/progress/demo_123
    """
    asyncio.create_task(_emit_demo_events(project_id))
    return {"status": "demo started", "view": f"/progress/{project_id}"}


async def _emit_demo_events(project_id: str):
    emit(project_id, "pipeline.start", node_id="pipeline")
    await asyncio.sleep(0.3)

    vid_id = f"vid_{uuid.uuid4().hex[:8]}"
    emit(project_id, "ingestion.complete", node_id="ingestion", parent_id="pipeline",
         videos=[{"id": vid_id, "filename": "clip_01.mp4"}])
    await asyncio.sleep(0.5)

    tracer = AgentTracer(project_id, "editing")
    tracer.on_agent_start(max_turns=50)
    await asyncio.sleep(0.3)

    tool_specs = [
        ("add_clip", {"source_video": "video_1", "start_s": 2.0, "end_s": 8.5}),
        ("add_clip", {"source_video": "video_1", "start_s": 15.0, "end_s": 22.0}),
        ("add_subtitle", {"text": "This is wild!", "start_s": 0.0, "end_s": 3.0}),
        ("search_and_download_asset", {"query": "surprised pikachu", "category": "meme"}),
        ("add_overlay", {"asset_path": "assets/memes/pikachu.gif", "at_s": 4.0}),
        ("get_composition_state", {}),
    ]

    demo_model = "azure/openai/gpt-5.2"
    for i, (tool_name, tool_args) in enumerate(tool_specs):
        fake_msgs = [
            {"role": "system", "content": "You are the Editing Agent for Open-Stitch..."},
            {"role": "user", "content": f"Build a short-form edit. Turn {i+1}."},
        ]
        tracer.on_llm_start(messages=fake_msgs, model=demo_model)
        await asyncio.sleep(0.4)

        accumulated = ""
        for word in ["Analyzing", " the", " footage", " and", " selecting", f" {tool_name}", "..."]:
            accumulated += word
            tracer.on_llm_chunk(word, accumulated)
            await asyncio.sleep(0.08)

        tc_id = f"call_{uuid.uuid4().hex[:8]}"
        prompt_tok = 1200 + i * 350
        completion_tok = 80 + i * 25
        tracer.on_llm_end(
            content=None,
            tool_calls=[{"id": tc_id, "function": {"name": tool_name}}],
            usage={"prompt_tokens": prompt_tok, "completion_tokens": completion_tok,
                   "total_tokens": prompt_tok + completion_tok},
        )
        await asyncio.sleep(0.2)

        tracer.on_tool_start(tc_id, tool_name, tool_args)
        await asyncio.sleep(0.6 + (0.4 if "search" in tool_name else 0))

        result = json.dumps({"id": f"seq_{i}", "status": "ok", "output_start_s": i * 3.0})
        tracer.on_tool_end(tc_id, tool_name, result)
        await asyncio.sleep(0.2)

    tracer.on_llm_start(
        messages=[{"role": "user", "content": "Finalize the composition."}],
        model=demo_model,
    )
    await asyncio.sleep(0.3)
    tracer.on_llm_end(
        content="Composition complete. 6 clips with subtitles and meme overlay.",
        tool_calls=None,
        usage={"prompt_tokens": 4200, "completion_tokens": 187, "total_tokens": 4387},
    )
    tracer.on_agent_end(summary="Built a 22-second edit with 2 clips, 1 subtitle, and a meme overlay.")
    await asyncio.sleep(0.3)

    emit(project_id, "render.start", node_id="render", parent_id="pipeline")
    await asyncio.sleep(1.5)
    emit(project_id, "render.end", node_id="render", outputUri="data/output/demo.mp4")
    await asyncio.sleep(0.3)

    emit(project_id, "pipeline.end", node_id="pipeline", status="complete")
