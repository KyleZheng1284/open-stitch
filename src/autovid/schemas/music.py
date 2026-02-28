"""Music track schemas for the Music Agent.

The Music Agent selects background music, trims/loops to fit clip duration,
and auto-generates duck points from transcript timestamps so music volume
lowers during speech segments.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class DuckPoint(BaseModel):
    """A time range where background music volume should be reduced.

    Generated automatically from transcript speech segments. During these
    ranges, music volume drops to duck_volume so speech remains clear.
    FFmpeg implements this via the sidechaincompress or volume filters.
    """

    start_ms: int = Field(ge=0, description="Duck start time in clip timeline")
    end_ms: int = Field(ge=0, description="Duck end time in clip timeline")
    duck_volume: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Volume during ducking (0.05 = barely audible)",
    )

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class MusicTrack(BaseModel):
    """A selected background music track with playback configuration.

    Produced by the Music Agent. The track_uri points to the audio file
    in the sandbox or object store. Duck points are auto-computed from
    the transcript so music volume drops during speech.
    """

    track_id: str = Field(description="Unique track identifier")
    source: str = Field(
        description="Source: epidemic_sound, mubert, local_library"
    )
    track_uri: str = Field(
        description="URI of the audio file (sandbox path or object store)"
    )
    title: str | None = Field(default=None, description="Track title")
    artist: str | None = Field(default=None, description="Track artist")
    mood_tags: list[str] = Field(
        default_factory=list,
        description="Mood descriptors: chill, upbeat, dramatic, lo-fi",
    )
    bpm: int | None = Field(
        default=None, ge=1, description="Beats per minute if known"
    )
    duration_ms: int = Field(gt=0, description="Track duration in milliseconds")
    volume: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Base volume relative to speech (0.0-1.0)",
    )
    duck_points: list[DuckPoint] = Field(
        default_factory=list,
        description="Auto-generated from transcript speech segments",
    )
    fade_in_ms: int = Field(
        default=2000, ge=0, description="Fade-in duration at track start"
    )
    fade_out_ms: int = Field(
        default=3000, ge=0, description="Fade-out duration at track end"
    )

    def total_duck_duration_ms(self) -> int:
        """Total time the music spends ducked."""
        return sum(dp.duration_ms for dp in self.duck_points)

    def effective_volume_at(self, timestamp_ms: int) -> float:
        """Get the effective volume at a specific timestamp.

        Returns duck_volume if within a duck point, else base volume.
        """
        for dp in self.duck_points:
            if dp.start_ms <= timestamp_ms <= dp.end_ms:
                return dp.duck_volume
        return self.volume
