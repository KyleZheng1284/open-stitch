"""Audio mixer — FFmpeg-based music ducking + SFX layering.

Runs as a post-processing step after Remotion renders the visual layers.
Handles background music with auto-ducking during speech, SFX placement
at specific timestamps, and volume normalization.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas.music import DuckPoint, MusicTrack

logger = logging.getLogger(__name__)


class AudioMixer:
    """Mix audio layers onto Remotion-rendered video."""

    async def mix(
        self,
        video_path: str,
        music_track: MusicTrack | None,
        sfx_inserts: list[dict[str, Any]],
        output_path: str,
        sandbox_id: str,
    ) -> str:
        """Mix all audio layers and return the output path.

        1. Layer background music with ducking at speech segments
        2. Layer SFX at precise timestamps
        3. Normalize output loudness to -14 LUFS
        """
        logger.info(
            "Mixing audio: music=%s, %d SFX inserts",
            music_track.track_uri if music_track else "none",
            len(sfx_inserts),
        )

        # TODO: Build FFmpeg filter graph for ducking + SFX
        # TODO: Execute via sandbox_run_ffmpeg
        # TODO: Normalize loudness

        return output_path
