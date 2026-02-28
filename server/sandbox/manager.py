"""Docker sandbox lifecycle management."""
from __future__ import annotations

import logging
import uuid

from server.config import get_settings

logger = logging.getLogger(__name__)

_containers: dict[str, dict] = {}


async def create_sandbox(job_id: str) -> str:
    """Spawn a sandbox container and return its ID."""
    s = get_settings()
    sandbox_id = f"sandbox_{uuid.uuid4().hex[:8]}"

    try:
        import docker
        client = docker.from_env()
        container = client.containers.run(
            s.sandbox_image,
            detach=True,
            name=sandbox_id,
            ports={"9876/tcp": None},
            mem_limit="8g",
            cpu_count=4,
            tmpfs={"/tmp": "size=2g"},
            remove=False,
        )
        port = container.ports.get("9876/tcp", [{}])[0].get("HostPort", "9876")
        _containers[sandbox_id] = {"container": container, "port": port, "job_id": job_id}
        logger.info("Sandbox %s created on port %s", sandbox_id, port)
    except Exception as e:
        logger.warning("Docker not available, using mock sandbox: %s", e)
        _containers[sandbox_id] = {"port": "9876", "job_id": job_id, "mock": True}

    return sandbox_id


async def destroy_sandbox(sandbox_id: str):
    """Stop and remove a sandbox container."""
    info = _containers.pop(sandbox_id, None)
    if info and "container" in info:
        try:
            info["container"].stop(timeout=10)
            info["container"].remove()
        except Exception as e:
            logger.warning("Failed to remove sandbox %s: %s", sandbox_id, e)


def get_sandbox_url(sandbox_id: str) -> str:
    info = _containers.get(sandbox_id, {})
    port = info.get("port", "9876")
    return f"http://localhost:{port}"
