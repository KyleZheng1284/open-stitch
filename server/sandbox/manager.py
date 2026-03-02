"""Docker sandbox lifecycle management.

Uses a single persistent container with data/ volume-mounted.
New uploads are immediately visible since the mount is live.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx

from server.config import get_settings

logger = logging.getLogger(__name__)

_DATA_DIR = str(Path("data").resolve())
_CONTAINER_NAME = "autovid-sandbox"

# Singleton sandbox state
_sandbox: dict | None = None


async def create_sandbox(job_id: str) -> str:
    """Get or create the persistent sandbox container."""
    global _sandbox

    # Reuse existing if healthy
    if _sandbox and not _sandbox.get("mock"):
        try:
            port = _sandbox["port"]
            resp = httpx.get(f"http://localhost:{port}/health", timeout=3.0)
            if resp.status_code == 200:
                logger.info("Reusing sandbox on port %s", port)
                return _CONTAINER_NAME
        except Exception:
            logger.info("Existing sandbox unhealthy, recreating")
            _sandbox = None

    s = get_settings()

    try:
        import docker
        client = docker.from_env()

        # Remove stale container if exists
        try:
            old = client.containers.get(_CONTAINER_NAME)
            old.stop(timeout=5)
            old.remove()
            logger.info("Removed stale sandbox container")
        except Exception:
            pass

        container = client.containers.run(
            s.sandbox_image,
            detach=True,
            name=_CONTAINER_NAME,
            ports={"9876/tcp": ("0.0.0.0", 9876)},
            volumes={_DATA_DIR: {"bind": "/workspace/data", "mode": "rw"}},
            mem_limit="32g",
            cpu_count=8,
            shm_size="8g",
            tmpfs={"/tmp": "size=8g"},
            remove=False,
        )

        # Wait for server to be ready
        for _ in range(10):
            time.sleep(1)
            try:
                resp = httpx.get("http://localhost:9876/health", timeout=3.0)
                if resp.status_code == 200:
                    break
            except Exception:
                pass

        _sandbox = {"container": container, "port": "9876", "job_id": job_id}
        logger.info("Sandbox ready on port 9876 (data mounted at /workspace/data)")

    except Exception as e:
        logger.warning("Docker not available, using ffmpeg fallback: %s", e)
        _sandbox = {"port": "9876", "job_id": job_id, "mock": True}

    return _CONTAINER_NAME


async def destroy_sandbox(sandbox_id: str):
    """No-op for persistent sandbox. Container stays running."""
    pass


def get_sandbox_url(sandbox_id: str) -> str:
    port = _sandbox["port"] if _sandbox else "9876"
    return f"http://localhost:{port}"


def is_mock(sandbox_id: str) -> bool:
    return (_sandbox or {}).get("mock", False)
