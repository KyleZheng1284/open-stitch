"""Chunk metadata store — read/write interface for Phase 1 results.

Wraps database operations for ChunkMetadata records. Agents query this
store to get dense VLM analysis, transcripts, and audio features.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from autovid.schemas.chunk import ChunkMetadata

logger = logging.getLogger(__name__)


class ChunkStore:
    """Read/write interface for chunk metadata."""

    async def store(self, metadata: ChunkMetadata) -> None:
        """Persist a chunk's metadata after Phase 1 processing."""
        logger.info(
            "Storing chunk %s (video=%s, status=%s)",
            metadata.chunk_id,
            metadata.video_id,
            metadata.processing_status,
        )
        # TODO: Upsert into chunks table via SQLAlchemy

    async def get(self, chunk_id: str) -> ChunkMetadata | None:
        """Retrieve a single chunk's metadata."""
        # TODO: Query from database
        return None

    async def get_by_video(self, video_id: str) -> list[ChunkMetadata]:
        """Get all chunks for a video, ordered by chunk_index."""
        # TODO: Query from database ORDER BY chunk_index
        return []

    async def get_by_project(self, project_id: str) -> list[ChunkMetadata]:
        """Get all chunks for a project, across all videos."""
        # TODO: Query from database ORDER BY video_id, chunk_index
        return []

    async def update_transcript(
        self, chunk_id: str, transcript: list[dict[str, Any]]
    ) -> None:
        """Update the transcript field after ASR completes."""
        # TODO: Update chunks.transcript WHERE id = chunk_id
        pass

    async def update_vlm_analysis(
        self, chunk_id: str, analysis: dict[str, Any]
    ) -> None:
        """Update the VLM analysis field after VLM processing completes."""
        # TODO: Update chunks.vlm_analysis WHERE id = chunk_id
        pass

    async def update_audio_features(
        self, chunk_id: str, features: dict[str, Any]
    ) -> None:
        """Update audio features after Audio Analyzer completes."""
        # TODO: Update chunks.audio_features WHERE id = chunk_id
        pass
