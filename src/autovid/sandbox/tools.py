"""LangGraph tool wrappers for sandbox operations.

These tools are registered in the agent graph and callable by any agent.
They wrap the SandboxClient with structured input/output types.
"""
from __future__ import annotations

import logging
from typing import Any

from .client import SandboxClient
from .schemas import AssetInfo, ExecResult, FileInfo, RenderResult

logger = logging.getLogger(__name__)


async def sandbox_list_files(client: SandboxClient, path: str = "") -> list[FileInfo]:
    """List files in a sandbox directory."""
    raw = await client.list_files(path)
    return [FileInfo(**f) for f in raw]


async def sandbox_read_file(client: SandboxClient, path: str) -> str:
    """Read a file from the sandbox."""
    return await client.read_file(path)


async def sandbox_write_file(
    client: SandboxClient, path: str, content: str
) -> None:
    """Write a file to the sandbox."""
    await client.write_file(path, content)


async def sandbox_delete_file(client: SandboxClient, path: str) -> None:
    """Delete a file from the sandbox."""
    await client.delete_file(path)


async def sandbox_exec(
    client: SandboxClient, command: str, timeout_s: int = 300
) -> ExecResult:
    """Execute a shell command inside the sandbox."""
    result = await client.exec(command, timeout=timeout_s)
    return ExecResult(**result)


async def sandbox_render_remotion(
    client: SandboxClient,
    timeline_json: dict[str, Any],
    output_path: str,
) -> RenderResult:
    """Render a Remotion composition inside the sandbox."""
    result = await client.render_remotion(timeline_json, output_path)
    return RenderResult(
        exit_code=result.get("exit_code", 1),
        output_path=result.get("output_path", ""),
        output_size=result.get("output_size", 0),
    )


async def sandbox_run_ffmpeg(
    client: SandboxClient, args: list[str], timeout_s: int = 300
) -> ExecResult:
    """Run an FFmpeg command inside the sandbox."""
    result = await client.run_ffmpeg(args, timeout=timeout_s)
    return ExecResult(**result)


async def sandbox_list_assets(
    client: SandboxClient, category: str
) -> list[AssetInfo]:
    """List available assets by category."""
    raw = await client.list_assets(category)
    return [AssetInfo(**a) for a in raw]
