"""Music Agent — selects and places background music.

Runs in parallel with Subtitle and Meme/SFX agents. Selects background
music based on mood tags derived from the style prompt, trims/loops to
fit clip duration, and generates duck points from transcript timestamps.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas import ProjectRequest
from autovid.schemas.composition import RemotionComposition
from autovid.schemas.music import DuckPoint, MusicTrack
from autovid.schemas.transcript import Transcript

from .remotion_tools import remotion_add_audio

logger = logging.getLogger(__name__)


class MusicAgent:
    """Selects background music and adds audio layers to the composition."""

    async def run(
        self,
        composition: RemotionComposition,
        chunks: list[Any],
        project: ProjectRequest,
    ) -> None:
        """Select music and add to composition with auto-ducking."""
        if not project.preferences.include_background_music:
            logger.info("Music agent: background music disabled, skipping")
            return

        mood = project.preferences.music_mood or "chill"
        logger.info("Music agent: selecting track with mood '%s'", mood)

        # TODO: Select track from local library / Epidemic Sound / Mubert
        # TODO: Trim/loop to match composition duration
        # TODO: Generate duck points from transcript speech segments
        # TODO: Call remotion_add_audio

        logger.info("Music agent complete: %d audio layers", len(composition.audio_layers))

    async def select_background_track(
        self,
        mood_tags: list[str],
        duration_s: float,
        energy_profile: list[float] | None = None,
    ) -> MusicTrack | None:
        """Search and select a background music track.

        Sources (in priority order):
        1. Local royalty-free library (config/assets/music/)
        2. Epidemic Sound API (if configured)
        3. Mubert API (if configured)
        """
        # TODO: Implement music source search
        logger.info(
            "Searching for track: mood=%s, duration=%.1fs", mood_tags, duration_s
        )
        return None

    @staticmethod
    def generate_duck_points(
        transcript: Transcript,
        ramp_ms: int = 200,
        duck_volume: float = 0.05,
    ) -> list[DuckPoint]:
        """Generate volume duck points from transcript speech segments.

        Music volume drops during speech so dialog remains clear.
        Includes a ramp-in/ramp-out for smooth volume transitions.
        """
        speech_segments = transcript.speech_segments(gap_threshold_ms=300)
        duck_points: list[DuckPoint] = []
        for start_ms, end_ms in speech_segments:
            duck_points.append(
                DuckPoint(
                    start_ms=max(0, start_ms - ramp_ms),
                    end_ms=end_ms + ramp_ms,
                    duck_volume=duck_volume,
                )
            )
        return duck_points
