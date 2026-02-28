"""Meme/SFX Agent — places meme overlays and sound effects.

Runs in parallel with Subtitle and Music agents on z-index 5-10 (overlays)
and z=-1 (audio). Reads VLM edit signals and subject bounding boxes to
decide meme/SFX placement. Position coordinates come from VLM spatial
grounding.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas import ProjectRequest
from autovid.schemas.composition import RemotionComposition
from autovid.schemas.vlm import ChunkVLMAnalysis, SecondAnalysis

from .remotion_tools import remotion_add_audio, remotion_add_overlay

logger = logging.getLogger(__name__)

# Edit signal -> SFX/meme mapping
SIGNAL_SFX_MAP: dict[str, str] = {
    "awkward_pause": "assets/sfx/vine_boom.mp3",
    "reaction": "assets/sfx/bruh.mp3",
    "punchline": "assets/sfx/airhorn.mp3",
    "energy_shift": "assets/sfx/record_scratch.mp3",
}

SIGNAL_MEME_MAP: dict[str, str] = {
    "reaction": "assets/memes/surprised_pikachu.png",
    "awkward_pause": "assets/memes/this_is_fine.png",
}


class MemeSFXAgent:
    """Places meme overlays and sound effects based on VLM edit signals."""

    async def run(
        self,
        composition: RemotionComposition,
        chunks: list[Any],
        project: ProjectRequest,
    ) -> None:
        """Scan VLM analysis for meme-able moments and place overlays/SFX."""
        if not project.preferences.include_memes and not project.preferences.include_sfx:
            logger.info("Meme/SFX agent: both disabled, skipping")
            return

        logger.info("Meme/SFX agent: scanning for meme-able moments")

        # TODO: Iterate over sequences in composition
        # TODO: For each sequence, find VLM analysis for the time range
        # TODO: Check edit_signal on each second
        # TODO: If include_memes: place meme overlay at subject bbox
        # TODO: If include_sfx: place SFX at signal timestamp
        # TODO: Always add transition whoosh between sequences

        logger.info(
            "Meme/SFX agent complete: %d overlays, %d audio layers",
            len(composition.overlays),
            len(composition.audio_layers),
        )

    def detect_meme_moments(
        self,
        vlm_analysis: ChunkVLMAnalysis,
        style_prompt: str,
    ) -> list[dict[str, Any]]:
        """Identify moments suitable for meme/SFX placement.

        Uses VLM edit signals, subject bounding boxes, and emotion data
        to determine what to place where.
        """
        moments: list[dict[str, Any]] = []

        for sec in vlm_analysis.seconds:
            if sec.edit_signal is None:
                continue
            if sec.edit_signal_confidence < 0.5:
                continue

            moment: dict[str, Any] = {
                "second": sec.second,
                "timestamp_ms": sec.timestamp_ms,
                "signal": sec.edit_signal,
                "confidence": sec.edit_signal_confidence,
                "reason": sec.edit_signal_reason,
            }

            # Get subject position for overlay placement
            if sec.subjects:
                primary = sec.subjects[0]
                cx, cy = primary.bbox.center
                moment["position"] = (cx, cy)
                moment["face_emotion"] = primary.face_emotion

            # Map signal to suggested assets
            if sec.edit_signal in SIGNAL_SFX_MAP:
                moment["sfx"] = SIGNAL_SFX_MAP[sec.edit_signal]
            if sec.edit_signal in SIGNAL_MEME_MAP:
                moment["meme"] = SIGNAL_MEME_MAP[sec.edit_signal]

            moments.append(moment)

        return moments
