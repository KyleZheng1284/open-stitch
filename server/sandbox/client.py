"""HTTP client for the sandbox-server.js API.

Since the host data/ directory is volume-mounted at /workspace/data,
video files are accessible directly — no base64 upload needed. We only
need to rewrite source paths and write the timeline JSON.

Falls back to ffmpeg concat when Docker isn't available.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from server.schemas.composition import Composition
from server.sandbox.manager import create_sandbox, destroy_sandbox, get_sandbox_url, is_mock

logger = logging.getLogger(__name__)


def _host_to_sandbox_url(host_path: str, sandbox_url: str) -> str:
    """Convert host path like 'data/uploads/proj_x/file.mp4'
    to sandbox static URL like 'http://localhost:9876/static/uploads/proj_x/file.mp4'.

    The sandbox serves /workspace/data/ at /static/."""
    p = Path(host_path)
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "data":
            # Strip 'data/' prefix since /static/ already maps to /workspace/data/
            relative = str(Path(*parts[i + 1:]))
            return f"{sandbox_url}/static/{relative}"
    return f"{sandbox_url}/static/{host_path}"


async def render_composition(composition: Composition) -> str:
    """Render composition via sandbox Remotion. Returns output path on host."""
    sandbox_id = await create_sandbox(composition.clip_id)

    if is_mock(sandbox_id):
        logger.warning("Mock sandbox — skipping Remotion render, using ffmpeg fallback")
        await destroy_sandbox(sandbox_id)
        return await _ffmpeg_fallback(composition)

    base_url = get_sandbox_url(sandbox_id)

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Build timeline with sandbox HTTP URLs for Remotion to fetch
            timeline = composition.to_timeline_json()
            for layer in timeline["layers"]:
                if "source" in layer and layer["source"]:
                    layer["source"] = _host_to_sandbox_url(layer["source"], base_url)

            # Write timeline JSON to sandbox
            await client.post(f"{base_url}/file", json={
                "path": "intermediate/timeline.json",
                "content": json.dumps(timeline),
            })

            # Output goes to the mounted data dir so we can read it from host
            output_container = f"/workspace/data/output/{composition.clip_id}.mp4"

            # Trigger Remotion render
            resp = await client.post(f"{base_url}/remotion/render", json={
                "timeline": timeline,
                "output": output_container,
            })
            result = resp.json()

            if result.get("exit_code", 1) != 0:
                logger.error("Render failed: %s", result.get("stderr", ""))
                raise RuntimeError(f"Render failed: {result.get('stderr', 'unknown error')}")

            host_output = f"data/output/{composition.clip_id}.mp4"
            logger.info("Render complete: %s (%d bytes)", host_output, result.get("output_size", 0))
            return host_output

    finally:
        await destroy_sandbox(sandbox_id)


async def _ffmpeg_fallback(composition: Composition) -> str:
    """Simple ffmpeg concat when Docker sandbox isn't available.

    Trims each clip and concatenates them sequentially.
    No subtitles, overlays, or transitions — just cut + join.
    """
    import asyncio
    import subprocess
    import tempfile

    out_dir = Path("data/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{composition.clip_id}.mp4"

    if not composition.sequences:
        raise RuntimeError("No sequences in composition")

    trimmed: list[Path] = []
    tmpdir = Path(tempfile.mkdtemp(prefix="av_render_"))

    for i, seq in enumerate(composition.sequences):
        start_s = seq.start_ms / 1000
        dur_s = (seq.end_ms - seq.start_ms) / 1000
        clip_path = tmpdir / f"clip_{i}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_s:.3f}",
            "-i", seq.source_uri,
            "-t", f"{dur_s:.3f}",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            "-vf", f"scale={composition.width}:{composition.height}:force_original_aspect_ratio=decrease,"
                   f"pad={composition.width}:{composition.height}:(ow-iw)/2:(oh-ih)/2",
            str(clip_path),
        ]
        logger.info("Trimming clip %d: %.1fs-%.1fs from %s", i, start_s, start_s + dur_s, seq.source_uri)
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error("ffmpeg trim failed: %s", proc.stderr[-500:] if proc.stderr else "")
            raise RuntimeError(f"ffmpeg trim failed for clip {i}")
        trimmed.append(clip_path)

    if len(trimmed) == 1:
        import shutil
        shutil.move(str(trimmed[0]), str(output_path))
    else:
        concat_file = tmpdir / "concat.txt"
        concat_file.write_text("\n".join(f"file '{p}'" for p in trimmed))
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error("ffmpeg concat failed: %s", proc.stderr[-500:] if proc.stderr else "")
            raise RuntimeError("ffmpeg concat failed")

    logger.info("ffmpeg fallback render complete: %s", output_path)
    return str(output_path)
