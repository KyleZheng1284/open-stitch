"""Typed editing tools for legacy and graph synthesis flows."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.schemas.composition import Composition


@dataclass(slots=True)
class ToolContext:
    """Runtime context for legacy editing tool-calling loop."""

    composition: Composition
    key_to_path: dict[str, str]
    ingestion_data: dict[str, dict[str, Any]]
    sandbox_url: str
    video_durations: dict[str, float]


def plan_clip_specs(
    project: dict[str, Any],
    *,
    previous_failure: bool = False,
) -> list[dict[str, Any]]:
    """Build deterministic initial clip plan from project ingestion data."""
    videos = project.get("videos", [])
    ingestion = project.get("ingestion_data", {})
    structured_prompt = str(project.get("structured_prompt", "")).lower()
    force_fail_once = "force_fail_once" in structured_prompt

    clips: list[dict[str, Any]] = []
    for idx, video in enumerate(videos, 1):
        vid_id = video.id if hasattr(video, "id") else video.get("id", "")
        data = ingestion.get(vid_id, {})
        duration = float(data.get("duration_s", 0.0))
        if duration <= 0:
            continue
        start_s = 0.0
        end_s = min(duration, 8.0)

        if force_fail_once and not previous_failure and idx == 1:
            end_s = start_s

        clips.append(
            {
                "source_video": f"video_{idx}",
                "start_s": start_s,
                "end_s": end_s,
                "reason": "Initial synthesis pass from ingestion summaries.",
            }
        )

    return clips


def build_key_to_path(project: dict[str, Any]) -> dict[str, str]:
    """Build source video key lookup used by composition builders."""
    mapping: dict[str, str] = {}
    ingestion = project.get("ingestion_data", {})
    for idx, video in enumerate(project.get("videos", []), 1):
        vid_id = video.id if hasattr(video, "id") else video.get("id", "")
        local_path = (
            video.local_path
            if hasattr(video, "local_path")
            else video.get("local_path", "")
        )
        data = ingestion.get(vid_id, {})
        video_path = str(data.get("video_path") or local_path)
        mapping[f"video_{idx}"] = video_path
        if vid_id:
            mapping[str(vid_id)] = video_path
    return mapping


def build_composition_from_clip_specs(
    clip_specs: list[dict[str, Any]],
    key_to_path: dict[str, str],
) -> Composition:
    """Create a Composition from clip specs."""
    composition = Composition()
    cursor_ms = 0

    for clip in clip_specs:
        source_key = str(clip.get("source_video", ""))
        source_uri = key_to_path.get(source_key, "")
        if not source_uri:
            raise ValueError(f"Unknown source video key: {source_key}")

        start_s = float(clip.get("start_s", 0.0))
        end_s = float(clip.get("end_s", 0.0))
        if end_s <= start_s:
            raise ValueError(f"Invalid clip range for {source_key}: {start_s}-{end_s}")

        start_ms = int(start_s * 1000)
        end_ms = int(end_s * 1000)
        composition.add_sequence(
            source_uri=source_uri,
            start_ms=start_ms,
            end_ms=end_ms,
            position_ms=cursor_ms,
            speed=1.0,
        )
        cursor_ms += end_ms - start_ms

    return composition


def timeline_from_composition_dict(composition_payload: dict[str, Any]) -> dict[str, Any]:
    """Convert serialized composition payload to timeline JSON."""
    composition = Composition.model_validate(dict(composition_payload))
    return composition.to_timeline_json()


EDITING_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add_clip",
            "description": "Append a source clip to the output timeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_video": {"type": "string"},
                    "start_s": {"type": "number"},
                    "end_s": {"type": "number"},
                    "speed": {"type": "number"},
                },
                "required": ["source_video", "start_s", "end_s"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_subtitle",
            "description": "Add a subtitle in output timeline seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "start_s": {"type": "number"},
                    "end_s": {"type": "number"},
                    "style": {"type": "string"},
                },
                "required": ["text", "start_s", "end_s"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_overlay",
            "description": "Add image/gif overlay in output timeline seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_path": {"type": "string"},
                    "at_s": {"type": "number"},
                    "duration_s": {"type": "number"},
                },
                "required": ["asset_path", "at_s"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_audio",
            "description": "Add audio layer in output timeline seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audio_path": {"type": "string"},
                    "at_s": {"type": "number"},
                    "volume": {"type": "number"},
                },
                "required": ["audio_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_download_asset",
            "description": "Create a local placeholder asset path for meme/SFX/music.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["query", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_assets",
            "description": "List locally available placeholder assets.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_image_slide",
            "description": "Add a photo as a full-screen slide with animation. Use for image files (JPG/PNG). Each slide plays for duration_s then the next item starts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Key like 'image_1' or full path"},
                    "duration_s": {"type": "number", "description": "How long to show (default 3.0)"},
                    "animation": {"type": "string", "enum": ["ken_burns", "zoom_in", "pan_left", "fade", "none"]},
                },
                "required": ["image_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_composition_state",
            "description": "Return composition counts and duration.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


async def dispatch_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> str:
    """Dispatch one legacy editing tool call."""
    handlers = {
        "add_clip": _add_clip,
        "add_subtitle": _add_subtitle,
        "add_overlay": _add_overlay,
        "add_audio": _add_audio,
        "add_image_slide": _add_image_slide,
        "search_and_download_asset": _search_and_download_asset,
        "list_available_assets": _list_available_assets,
        "get_composition_state": _get_composition_state,
    }
    handler = handlers.get(name)
    if handler is None:
        return json.dumps({"ok": False, "error": f"Unknown tool: {name}"})
    try:
        return json.dumps(handler(args, ctx))
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def _add_clip(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    source_key = str(args.get("source_video", ""))
    source_uri = ctx.key_to_path.get(source_key, "")
    if not source_uri:
        raise ValueError(f"Unknown source video: {source_key}")

    start_s = float(args.get("start_s", 0.0))
    end_s = float(args.get("end_s", 0.0))
    speed = float(args.get("speed", 1.0))
    if end_s <= start_s:
        raise ValueError("end_s must be greater than start_s")
    if speed <= 0:
        raise ValueError("speed must be > 0")

    start_ms = int(start_s * 1000)
    end_ms = int(end_s * 1000)
    position_ms = ctx.composition.total_duration_ms
    seq_id = ctx.composition.add_sequence(
        source_uri=source_uri,
        start_ms=start_ms,
        end_ms=end_ms,
        position_ms=position_ms,
        speed=speed,
    )
    clip_dur_ms = int((end_ms - start_ms) / speed)
    return {
        "ok": True,
        "id": seq_id,
        "output_start_s": round(position_ms / 1000, 3),
        "output_end_s": round((position_ms + clip_dur_ms) / 1000, 3),
        "total_duration_s": round(ctx.composition.total_duration_ms / 1000, 3),
    }


def _add_subtitle(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    text = str(args.get("text", "")).strip()
    if not text:
        raise ValueError("text is required")
    start_ms = int(float(args.get("start_s", 0.0)) * 1000)
    end_ms = int(float(args.get("end_s", 0.0)) * 1000)
    if end_ms <= start_ms:
        raise ValueError("end_s must be greater than start_s")
    style = str(args.get("style", "tiktok_pop"))
    subtitle_id = ctx.composition.add_subtitle(
        text=text,
        start_ms=start_ms,
        end_ms=end_ms,
        style=style,
    )
    return {"ok": True, "id": subtitle_id}


def _normalize_asset_path(raw_path: str) -> str:
    """Ensure asset paths include the data/ prefix so sandbox URL rewriting works."""
    p = raw_path.strip()
    if p.startswith("http://") or p.startswith("https://"):
        return p
    if not p.startswith("data/"):
        if p.startswith("assets/"):
            p = f"data/{p}"
        elif not p.startswith("/"):
            p = f"data/assets/{p}"
    return p


def _add_overlay(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    asset_path = _normalize_asset_path(str(args.get("asset_path", "")))
    if not asset_path:
        raise ValueError("asset_path is required")
    at_ms = int(float(args.get("at_s", 0.0)) * 1000)
    duration_ms = int(float(args.get("duration_s", 2.0)) * 1000)
    overlay_id = ctx.composition.add_overlay(
        asset_uri=asset_path,
        at_ms=at_ms,
        duration_ms=duration_ms,
    )
    return {"ok": True, "id": overlay_id}


def _add_audio(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    audio_path = _normalize_asset_path(str(args.get("audio_path", "")))
    if not audio_path:
        raise ValueError("audio_path is required")
    at_ms = int(float(args.get("at_s", 0.0)) * 1000)
    volume = float(args.get("volume", 0.8))
    fade_in_ms = int(float(args.get("fade_in_s", 0.0)) * 1000)
    fade_out_ms = int(float(args.get("fade_out_s", 0.0)) * 1000)
    audio_id = ctx.composition.add_audio(
        audio_uri=audio_path,
        start_ms=at_ms,
        volume=volume,
        fade_in_ms=fade_in_ms,
        fade_out_ms=fade_out_ms,
    )
    return {"ok": True, "id": audio_id, "asset_path": audio_path, "start_s": at_ms / 1000, "volume": volume}


def _add_image_slide(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    image_key = str(args.get("image_path", "")).strip()
    if not image_key:
        raise ValueError("image_path is required")

    image_uri = ctx.key_to_path.get(image_key, image_key)
    duration_ms = int(float(args.get("duration_s", 3.0)) * 1000)
    animation = str(args.get("animation", "ken_burns"))
    position_ms = ctx.composition.total_duration_ms

    slide_id = ctx.composition.add_image_slide(
        image_uri=image_uri,
        position_ms=position_ms,
        duration_ms=duration_ms,
        animation=animation,
    )
    return {
        "ok": True,
        "id": slide_id,
        "output_start_s": round(position_ms / 1000, 3),
        "output_end_s": round((position_ms + duration_ms) / 1000, 3),
        "total_duration_s": round(ctx.composition.total_duration_ms / 1000, 3),
    }


def _search_and_download_asset(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _ = ctx
    query = str(args.get("query", "")).strip()
    category = str(args.get("category", "misc")).strip().lower() or "misc"
    if not query:
        raise ValueError("query is required")

    slug = _slugify(query)
    out_dir = Path("data/assets") / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.txt"
    out_path.write_text(f"placeholder asset for query: {query}\n")
    return {"ok": True, "asset_path": str(out_path)}


def _list_available_assets(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _ = args, ctx
    root = Path("data/assets")
    if not root.exists():
        return {"ok": True, "assets": []}
    assets = sorted(str(path) for path in root.rglob("*") if path.is_file())
    return {"ok": True, "assets": assets}


def _get_composition_state(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _ = args
    return {
        "ok": True,
        "clips": len(ctx.composition.sequences),
        "image_slides": len(ctx.composition.image_slides),
        "subtitles": len(ctx.composition.subtitles),
        "overlays": len(ctx.composition.overlays),
        "audio_layers": len(ctx.composition.audio_layers),
        "duration_s": round(ctx.composition.total_duration_ms / 1000, 3),
    }


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "asset"
