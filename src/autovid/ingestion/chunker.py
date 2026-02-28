"""Video chunking: scene-detect + temporal splitting.

Splits videos into 10-30 second chunks at scene boundaries. Falls back
to fixed-interval splits if scene detection yields too few/many segments.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_MIN_S = 10
DEFAULT_CHUNK_MAX_S = 30
SCENE_THRESHOLD = 0.3


class Chunker:
    """Split videos into time-aligned chunks for parallel processing."""

    def __init__(
        self,
        min_chunk_s: int = DEFAULT_CHUNK_MIN_S,
        max_chunk_s: int = DEFAULT_CHUNK_MAX_S,
        scene_threshold: float = SCENE_THRESHOLD,
    ) -> None:
        self.min_chunk_s = min_chunk_s
        self.max_chunk_s = max_chunk_s
        self.scene_threshold = scene_threshold

    async def split(self, video_uri: str) -> list[dict[str, Any]]:
        """Split a video into chunks.

        Strategy:
        1. Run FFmpeg scene detection: select='gt(scene,threshold)'
        2. Merge short scenes into chunks (min 10s)
        3. Split long scenes at fixed intervals (max 30s)
        4. Extract audio per chunk for ASR

        Returns list of chunk dicts with:
        - video_uri: URI of the chunk video
        - audio_uri: URI of the extracted chunk audio
        - start_ms: Start time in source video
        - end_ms: End time in source video
        """
        # TODO: Probe video for duration
        # TODO: Run FFmpeg scene detection
        # TODO: Compute chunk boundaries
        # TODO: Split video and audio per chunk
        # TODO: Upload chunks to object store

        logger.info("Chunking video: %s", video_uri)
        return []
