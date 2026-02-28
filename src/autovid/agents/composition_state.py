"""Composition state manager.

Manages the in-memory RemotionComposition state with thread-safe access.
Used by the Director Agent to create, snapshot, and serialize compositions.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from autovid.schemas.composition import RemotionComposition
from autovid.schemas.timeline import TimelineJSON

logger = logging.getLogger(__name__)


class CompositionStateManager:
    """Manages RemotionComposition lifecycle and serialization."""

    def __init__(self) -> None:
        self._compositions: dict[str, RemotionComposition] = {}

    def create(self, clip_id: str, width: int = 1080, height: int = 1920) -> RemotionComposition:
        """Create a new composition and register it."""
        comp = RemotionComposition(clip_id=clip_id, width=width, height=height)
        self._compositions[clip_id] = comp
        logger.info("Created composition %s (%dx%d)", clip_id, width, height)
        return comp

    def get(self, clip_id: str) -> RemotionComposition | None:
        """Get a composition by clip ID."""
        return self._compositions.get(clip_id)

    def to_timeline_json(self, clip_id: str) -> TimelineJSON:
        """Serialize composition to TimelineJSON for sandbox rendering."""
        comp = self._compositions.get(clip_id)
        if comp is None:
            raise ValueError(f"Composition not found: {clip_id}")
        return TimelineJSON.from_composition(comp)

    def to_json_string(self, clip_id: str) -> str:
        """Serialize composition to JSON string for sandbox file write."""
        timeline = self.to_timeline_json(clip_id)
        return timeline.model_dump_json(indent=2)

    def snapshot(self, clip_id: str) -> dict[str, Any]:
        """Get a read-only snapshot of composition state for logging/tracing."""
        comp = self._compositions.get(clip_id)
        if comp is None:
            return {}
        return {
            "clip_id": clip_id,
            "sequences": len(comp.sequences),
            "overlays": len(comp.overlays),
            "subtitles": len(comp.subtitles),
            "audio_layers": len(comp.audio_layers),
            "total_duration_ms": comp.total_duration_ms,
        }

    def destroy(self, clip_id: str) -> None:
        """Remove a composition from memory."""
        self._compositions.pop(clip_id, None)
