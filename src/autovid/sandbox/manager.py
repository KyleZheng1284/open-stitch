"""Sandbox Manager — Docker container lifecycle management.

Creates, monitors, and destroys per-job sandbox containers.
Handles file staging (MinIO -> sandbox) and result collection.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.config import get_settings

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manage Docker sandbox containers for editing jobs."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._docker_client = None

    def _get_docker(self) -> Any:
        """Lazy-load Docker client."""
        if self._docker_client is None:
            import docker
            self._docker_client = docker.from_env()
        return self._docker_client

    async def create(self, job_id: str) -> str:
        """Spawn a new sandbox container for a job.

        Returns the sandbox container ID.
        """
        logger.info("Creating sandbox for job %s", job_id)
        client = self._get_docker()

        container = client.containers.run(
            image=self.settings.sandbox_image,
            name=f"autovid-sandbox-{job_id}",
            detach=True,
            network_mode=self.settings.sandbox_network,
            mem_limit=self.settings.sandbox_memory_limit,
            nano_cpus=int(float(self.settings.sandbox_cpu_limit) * 1e9),
            tmpfs={"/tmp": f"size=2G"},
            labels={"autovid.job_id": job_id},
        )

        logger.info("Sandbox created: %s (%s)", container.id[:12], container.name)
        return container.id

    async def stage_inputs(
        self,
        sandbox_id: str,
        chunk_uris: list[str],
        asset_uris: list[str],
    ) -> None:
        """Copy raw chunks and assets from MinIO into the sandbox."""
        logger.info(
            "Staging %d chunks + %d assets into sandbox %s",
            len(chunk_uris), len(asset_uris), sandbox_id[:12],
        )
        # TODO: Download from MinIO, upload to sandbox via HTTP API

    async def collect_outputs(self, sandbox_id: str) -> list[str]:
        """Copy rendered outputs from sandbox to MinIO.

        Returns list of MinIO URIs for exported files.
        """
        # TODO: List /workspace/output/ via sandbox API
        # TODO: Download each file and upload to MinIO
        return []

    async def destroy(self, sandbox_id: str) -> None:
        """Stop and remove a sandbox container."""
        logger.info("Destroying sandbox %s", sandbox_id[:12])
        client = self._get_docker()
        try:
            container = client.containers.get(sandbox_id)
            container.stop(timeout=10)
            container.remove(force=True)
        except Exception as e:
            logger.warning("Failed to destroy sandbox %s: %s", sandbox_id[:12], e)

    async def get_endpoint(self, sandbox_id: str) -> str:
        """Get the HTTP API endpoint for a sandbox container."""
        client = self._get_docker()
        container = client.containers.get(sandbox_id)
        # In network_mode=none, use container IP or port mapping
        return f"http://localhost:9876"  # TODO: proper endpoint resolution
