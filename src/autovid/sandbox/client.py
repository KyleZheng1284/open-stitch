"""Sandbox HTTP client.

Communicates with the sandbox-server.js API running inside each container.
All file operations and command executions go through this client.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SandboxClient:
    """HTTP client for the sandbox API."""

    def __init__(self, endpoint: str = "http://localhost:9876") -> None:
        self.endpoint = endpoint.rstrip("/")
        self._client = httpx.AsyncClient(timeout=600.0)

    async def health(self) -> dict[str, Any]:
        """Check sandbox health."""
        resp = await self._client.get(f"{self.endpoint}/health")
        resp.raise_for_status()
        return resp.json()

    async def list_files(self, path: str = "") -> list[dict[str, Any]]:
        """List files in a sandbox directory."""
        resp = await self._client.get(f"{self.endpoint}/files", params={"path": path})
        resp.raise_for_status()
        return resp.json().get("files", [])

    async def read_file(self, path: str) -> str:
        """Read a text file from the sandbox."""
        resp = await self._client.get(f"{self.endpoint}/file", params={"path": path})
        resp.raise_for_status()
        return resp.json().get("content", "")

    async def write_file(self, path: str, content: str, encoding: str = "utf-8") -> dict[str, Any]:
        """Write a file to the sandbox."""
        resp = await self._client.post(
            f"{self.endpoint}/file",
            json={"path": path, "content": content, "encoding": encoding},
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_file(self, path: str) -> dict[str, Any]:
        """Delete a file from the sandbox."""
        resp = await self._client.delete(f"{self.endpoint}/file", params={"path": path})
        resp.raise_for_status()
        return resp.json()

    async def exec(self, command: str, timeout: int = 300) -> dict[str, Any]:
        """Execute a shell command inside the sandbox."""
        resp = await self._client.post(
            f"{self.endpoint}/exec",
            json={"command": command, "timeout": timeout},
        )
        resp.raise_for_status()
        return resp.json()

    async def run_ffmpeg(self, args: list[str], timeout: int = 300) -> dict[str, Any]:
        """Run an FFmpeg command inside the sandbox."""
        resp = await self._client.post(
            f"{self.endpoint}/ffmpeg",
            json={"args": args, "timeout": timeout},
        )
        resp.raise_for_status()
        return resp.json()

    async def render_remotion(
        self, timeline: dict[str, Any], output: str
    ) -> dict[str, Any]:
        """Trigger a Remotion render inside the sandbox."""
        resp = await self._client.post(
            f"{self.endpoint}/remotion/render",
            json={"timeline": timeline, "output": output},
            timeout=600.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def list_assets(self, category: str) -> list[dict[str, Any]]:
        """List available assets by category (memes, sfx, music)."""
        resp = await self._client.get(
            f"{self.endpoint}/assets", params={"category": category}
        )
        resp.raise_for_status()
        return resp.json().get("assets", [])

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
