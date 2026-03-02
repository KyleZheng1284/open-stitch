"""Editing Agent -- tool-calling loop that builds compositions step by step.

The LLM acts as the human editor, iteratively calling tools to:
- Select video clips from the source footage
- Add subtitles from the transcript
- Search for and download memes, SFX, music
- Place overlays and audio at precise timestamps
- Self-check the composition before finishing

The agent decides when it's done. Soft cap of 50 turns for safety.
"""
from __future__ import annotations

import json
import logging

import httpx

from server.config import api_credentials_for, get_settings
from server.events import AgentTracer
from server.schemas.composition import Composition
from server.agents.tools import EDITING_TOOLS, ToolContext, dispatch_tool

logger = logging.getLogger(__name__)


# ── LLM Calls (async streaming) ──────────────────────────────────────

async def _call_llm_with_tools(
    messages: list[dict],
    tools: list[dict],
    *,
    tracer: AgentTracer | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 8192,
) -> dict:
    """Call LLM with tool definitions via streaming.

    Streams tokens in real-time through the tracer so the frontend can
    show "thinking..." state. Accumulates tool-call deltas and returns
    the full assistant message dict.
    """
    s = get_settings()
    use_model = model or s.editing_model
    use_temp = temperature if temperature is not None else s.editing_temperature

    payload = {
        "model": use_model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": use_temp,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    logger.info("LLM call: model=%s temp=%.1f", use_model, use_temp)

    api_key, base_url = api_credentials_for(use_model)
    async with httpx.AsyncClient(
        timeout=180.0,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    ) as client:
        accumulated_content = ""
        accumulated_tool_calls: dict[int, dict] = {}
        usage: dict = {}

        async with client.stream(
            "POST", f"{base_url}/chat/completions", json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break

                chunk = json.loads(data_str)

                if chunk.get("usage"):
                    usage = chunk["usage"]

                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})

                if delta.get("content"):
                    accumulated_content += delta["content"]
                    if tracer:
                        tracer.on_llm_chunk(delta["content"], accumulated_content)

                if delta.get("tool_calls"):
                    for tc_delta in delta["tool_calls"]:
                        idx = tc_delta["index"]
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": tc_delta.get("id", ""),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        entry = accumulated_tool_calls[idx]
                        if tc_delta.get("id"):
                            entry["id"] = tc_delta["id"]
                        fn = tc_delta.get("function", {})
                        if fn.get("name"):
                            entry["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            entry["function"]["arguments"] += fn["arguments"]

        tool_calls_list = (
            [accumulated_tool_calls[i] for i in sorted(accumulated_tool_calls)]
            or None
        )

        return {
            "role": "assistant",
            "content": accumulated_content or None,
            "tool_calls": tool_calls_list,
            "_usage": usage,
        }


# ── Video Context Builder ────────────────────────────────────────────

def _build_video_context(ingestion_data: dict) -> tuple[str, dict[str, str], dict[str, float]]:
    """Build per-media context and lookups.

    Returns (context_text, key_to_path, video_durations).
    Handles both video and image media types.
    """
    context_parts = []
    key_to_path: dict[str, str] = {}
    durations: dict[str, float] = {}
    video_idx = 0
    image_idx = 0

    for vid_id, data in ingestion_data.items():
        media_type = data.get("media_type", "video")
        file_path = data.get("video_path") or data.get("image_path", "")

        if media_type == "image":
            image_idx += 1
            key = f"image_{image_idx}"
            key_to_path[key] = file_path
            key_to_path[vid_id] = file_path
            durations[key] = 0

            summary = data.get("summary", "No description")
            context_parts.append(
                f"=== {key} (PHOTO) ===\n"
                f"Description: {summary}\n"
            )
        else:
            video_idx += 1
            key = f"video_{video_idx}"
            key_to_path[key] = file_path
            key_to_path[vid_id] = file_path

            duration = data.get("duration_s", 0)
            durations[key] = duration

            summary = data.get("summary", "No summary")
            asr = data.get("asr") or {}
            transcript = " ".join(s.get("text", "") for s in asr.get("sentences", [])) if asr else ""
            timeline = data.get("timeline", [])

            compact = []
            for entry in timeline:
                t = {
                    "t": entry.get("t", 0),
                    "action": entry.get("action", ""),
                    "energy": entry.get("energy", 0),
                    "edit_signal": entry.get("edit_signal", "hold"),
                    "speech": entry.get("speech", ""),
                }
                if entry.get("subjects"):
                    t["subjects"] = entry["subjects"]
                if entry.get("face"):
                    t["face"] = entry["face"]
                compact.append(t)

            context_parts.append(
                f"=== {key} ===\n"
                f"Duration: {duration:.1f}s\n"
                f"Summary: {summary}\n"
                f"Transcript: \"{transcript}\"\n"
                f"Per-second timeline ({len(compact)} entries):\n"
                f"{json.dumps(compact, indent=1)}\n"
            )

    return "\n".join(context_parts), key_to_path, durations


# ── System Prompt ────────────────────────────────────────────────────

def _build_messages(
    structured_prompt: str,
    video_context: str,
    video_keys: list[str],
    duration_info: str,
) -> list[dict]:
    """Build the initial message array for the tool-calling agent."""
    has_images = any(k.startswith("image_") for k in video_keys)
    has_videos = any(k.startswith("video_") for k in video_keys)

    image_tool_desc = ""
    if has_images:
        image_tool_desc = (
            "- add_image_slide: Add a photo as a full-screen slide with animation "
            "(ken_burns, zoom_in, pan_left, fade, none). Each slide plays back-to-back.\n"
        )

    if has_images and not has_videos:
        workflow = (
            "== WORKFLOW (PHOTO SLIDESHOW) ==\n"
            "1. Study the photo descriptions below.\n"
            "2. Use add_image_slide for each photo in narrative order. Each slide "
            "plays for duration_s then the next starts. Pick animations that match "
            "the mood (ken_burns for landscapes, zoom_in for details, etc.).\n"
            "3. Add subtitles for captions or text overlays.\n"
            "4. Search for and add background music using search_and_download_asset + add_audio.\n"
            "5. Use get_composition_state to verify.\n"
            "6. When done, STOP and summarize.\n\n"
        )
        start_instruction = "Build the slideshow now. Start by adding image slides."
    else:
        workflow = (
            "== WORKFLOW ==\n"
            "1. Study the media analysis below.\n"
            "2. Use add_clip to select the best video moments. Each clip plays "
            "right after the previous one.\n"
            + ("3. Use add_image_slide for photo slides between or alongside video clips.\n" if has_images else "")
            + "3. Use add_subtitle with EXACT words from the transcript.\n"
            "4. If the edit calls for it, search for memes, sound effects, or music "
            "using search_and_download_asset, then place them with add_overlay or add_audio.\n"
            "5. Use get_composition_state to verify.\n"
            "6. When done, STOP and summarize.\n\n"
        )
        start_instruction = "Build the composition now. Start by selecting clips."

    return [
        {
            "role": "system",
            "content": (
                "You are the Editing Agent for Open-Stitch. You ARE the human editor. "
                "Build a video composition step-by-step using your tools, exactly like "
                "a professional editor would in a timeline.\n\n"

                "== YOUR TOOLS ==\n"
                "- add_clip: Select a segment from a source video. Clips play back-to-back.\n"
                + image_tool_desc +
                "- add_subtitle: Add text overlay at a specific output-timeline time.\n"
                "- add_overlay: Place a meme/image at a timestamp (must download first).\n"
                "- add_audio: Add background music or SFX (must download first).\n"
                "- search_and_download_asset: Find and download a meme/SFX/music from the web.\n"
                "- list_available_assets: Check what assets are already available locally.\n"
                "- get_composition_state: Review what you've built so far.\n\n"

                + workflow +

                "== RULES ==\n"
                f"Available sources: {', '.join(video_keys)}\n"
                f"Durations: {duration_info}\n"
                "- add_clip start_s/end_s = timestamps WITHIN the source video\n"
                "- add_subtitle/add_overlay/add_audio times = OUTPUT timeline positions\n"
                "- Use only transcript words for subtitles -- don't invent text\n"
                "- Subtitles appear at the bottom of the screen by default\n"
                "- Add ALL spoken words as subtitles (auto-captions) for accessibility\n"
                "- Pick high-energy moments or edit_signal='cut' points for clips\n"
                "- speed: 1.0=normal, 0.5=slow-mo, 1.5=fast\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"== USER REQUEST ==\n{structured_prompt}\n\n"
                f"== MEDIA ANALYSIS ==\n{video_context}\n\n"
                + start_instruction
            ),
        },
    ]


# ── Agent Loop ───────────────────────────────────────────────────────

async def _run_tool_loop(
    messages: list[dict],
    ctx: ToolContext,
    *,
    tracer: AgentTracer | None = None,
    max_turns: int | None = None,
) -> str:
    """Run the tool-calling agent loop.

    The agent calls tools iteratively until it stops (no more tool_calls).
    Soft cap prevents runaway loops but the agent decides when it's done.
    """
    s = get_settings()
    max_turns = max_turns or s.max_tool_iterations

    if tracer:
        tracer.on_agent_start(max_turns=max_turns)

    for i in range(max_turns):
        if tracer:
            tracer.on_llm_start(messages=messages, model=s.editing_model)

        response = await _call_llm_with_tools(messages, EDITING_TOOLS, tracer=tracer)
        messages.append(response)

        tool_calls = response.get("tool_calls")
        usage = response.get("_usage", {})

        if tracer:
            tracer.on_llm_end(
                content=response.get("content"),
                tool_calls=tool_calls,
                usage=usage,
            )

        if not tool_calls:
            final = response.get("content", "")
            logger.info("Agent finished after %d turns: %s", i + 1, final[:200] if final else "(no summary)")
            if tracer:
                tracer.on_agent_end(summary=final[:500])
            return final

        for tc in tool_calls:
            tc_id = tc["id"]
            fn_name = tc["function"]["name"]
            fn_args_raw = tc["function"]["arguments"]
            fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw

            logger.info("[turn %d] %s(%s)", i, fn_name, json.dumps(fn_args)[:200])

            if tracer:
                tracer.on_tool_start(tc_id, fn_name, fn_args)

            result = await dispatch_tool(fn_name, fn_args, ctx)

            logger.info("   -> %s", result[:200])

            if tracer:
                tracer.on_tool_end(tc_id, fn_name, result)

            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": result,
            })

    logger.warning("Agent hit soft cap (%d turns)", max_turns)
    if tracer:
        tracer.on_agent_end(summary="Soft cap reached")
    return "Soft cap reached -- composition may be incomplete"


# ── Main Entry Points ────────────────────────────────────────────────

async def build_composition(
    project: dict,
    *,
    tracer: AgentTracer | None = None,
) -> Composition:
    """Build a composition via the multi-turn tool-calling agent loop.

    Does NOT render -- returns the Composition for the caller to render.
    Used by both the legacy path and the graph EditingSynthesisAgent.
    """
    project_id = project["id"]
    structured_prompt = project.get("structured_prompt", "")
    ingestion_data = project.get("ingestion_data", {})

    if not ingestion_data:
        raise RuntimeError("No ingestion data -- run ingestion first")

    if tracer is None:
        tracer = AgentTracer(project_id, "editing")

    video_context, key_to_path, durations = _build_video_context(ingestion_data)
    video_keys = sorted(k for k in key_to_path if k.startswith("video_")) + sorted(k for k in key_to_path if k.startswith("image_"))
    duration_info = ", ".join(
        f"{k}: {'photo' if k.startswith('image_') else f'{durations.get(k, 0):.1f}s'}"
        for k in video_keys
    )

    first_info = next(
        (data.get("info", {}) for data in ingestion_data.values() if data.get("info")),
        {},
    )
    src_w = int(first_info.get("width", 0))
    src_h = int(first_info.get("height", 0))
    if src_w > 0 and src_h > 0:
        if src_w >= src_h:
            comp_w, comp_h = 1920, 1080
        else:
            comp_w, comp_h = 1080, 1920
    else:
        comp_w, comp_h = 1080, 1920

    composition = Composition(width=comp_w, height=comp_h)
    logger.info("Composition dimensions: %dx%d (from source %dx%d)", comp_w, comp_h, src_w, src_h)

    from server.sandbox.manager import create_sandbox, get_sandbox_url
    sandbox_id = await create_sandbox(composition.clip_id)
    sandbox_url = get_sandbox_url(sandbox_id)

    ctx = ToolContext(
        composition=composition,
        key_to_path=key_to_path,
        ingestion_data=ingestion_data,
        sandbox_url=sandbox_url,
        video_durations=durations,
    )

    messages = _build_messages(structured_prompt, video_context, video_keys, duration_info)

    logger.info("Starting editing agent (tool-calling mode)...")
    await _run_tool_loop(messages, ctx, tracer=tracer)

    if not composition.sequences and not composition.image_slides:
        raise RuntimeError("Agent produced no clips or slides -- composition is empty")

    logger.info(
        "Composition ready: %d clips, %d slides, %d subtitles, %d overlays, %d audio, %.1fs total",
        len(composition.sequences),
        len(composition.image_slides),
        len(composition.subtitles),
        len(composition.overlays),
        len(composition.audio_layers),
        composition.total_duration_ms / 1000,
    )

    return composition


async def run_editing_agent(project: dict) -> str:
    """Full editing pipeline: tool-calling agent loop -> render."""
    composition = await build_composition(project)

    logger.info("Rendering via sandbox...")
    from server.sandbox.client import render_composition
    output_uri = await render_composition(composition, project_id=project["id"])

    return output_uri
