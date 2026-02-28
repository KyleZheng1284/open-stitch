"""HTTP client for the sandbox-server.js API."""
from __future__ import annotations

import json
import logging

import httpx

from server.schemas.composition import Composition
from server.sandbox.manager import create_sandbox, destroy_sandbox, get_sandbox_url

logger = logging.getLogger(__name__)


async def render_composition(composition: Composition) -> str:
    """Stage inputs, render via sandbox Remotion, return output path."""
    sandbox_id = await create_sandbox(composition.clip_id)
    base_url = get_sandbox_url(sandbox_id)

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Stage input videos
            for seq in composition.sequences:
                logger.info("Staging %s to sandbox", seq.source_uri)
                # Read local file and upload to sandbox
                with open(seq.source_uri, "rb") as f:
                    import base64
                    content_b64 = base64.b64encode(f.read()).decode()
                await client.post(f"{base_url}/file", json={
                    "path": f"input/{seq.id}.mp4",
                    "content": content_b64,
                    "encoding": "base64",
                })

            # Write timeline JSON
            timeline = composition.to_timeline_json()
            await client.post(f"{base_url}/file", json={
                "path": "intermediate/timeline.json",
                "content": json.dumps(timeline),
            })

            # Trigger Remotion render
            resp = await client.post(f"{base_url}/remotion/render", json={
                "timeline": timeline,
                "output": "/workspace/output/render.mp4",
            })
            result = resp.json()

            if result.get("exit_code", 1) != 0:
                logger.error("Render failed: %s", result.get("stderr", ""))
                raise RuntimeError(f"Render failed: {result.get('stderr', 'unknown error')}")

            output_path = result.get("output_path", "/workspace/output/render.mp4")
            logger.info("Render complete: %s (%d bytes)", output_path, result.get("output_size", 0))

            # Download output
            dl = await client.get(f"{base_url}/file", params={"path": "output/render.mp4"})
            dl_data = dl.json()

            # Save locally
            import base64
            from pathlib import Path
            out_dir = Path("data/output")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{composition.clip_id}.mp4"

            if dl_data.get("encoding") == "base64":
                out_path.write_bytes(base64.b64decode(dl_data["content"]))
            else:
                out_path.write_text(dl_data.get("content", ""))

            return str(out_path)

    finally:
        await destroy_sandbox(sandbox_id)
