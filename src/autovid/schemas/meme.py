"""Meme and SFX insert schemas for the Meme/SFX Agent.

The Meme/SFX Agent reads VLM edit signals (reaction, punchline, awkward_pause)
and subject bounding boxes to decide what memes/SFX to place, where, and when.
Position coordinates come directly from VLM spatial grounding.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .clip_spec import Keyframe


class MemeInsert(BaseModel):
    """A meme image/GIF overlay placed at a specific moment.

    Position comes from VLM bounding box data (e.g., thug_life_glasses
    positioned above detected face). Animation keyframes enable TikTok-style
    entrance effects (pop-in, bounce, slide-down).
    """

    type: str = Field(
        default="image_overlay", description="Insert type identifier"
    )
    at_ms: int = Field(
        ge=0, description="Placement timestamp in clip timeline"
    )
    duration_ms: int = Field(
        default=2000, gt=0, description="How long the overlay stays visible"
    )
    image_uri: str = Field(description="URI of the meme image/GIF file")
    position: tuple[float, float] = Field(
        default=(0.5, 0.3),
        description="(x, y) normalized placement from VLM spatial reasoning",
    )
    scale: float = Field(
        default=0.3, gt=0.0, description="Scale relative to frame"
    )
    rotation: float = Field(default=0.0, description="Rotation in degrees")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    z_index: int = Field(
        default=10, ge=0, description="Stacking order (5-10 range for memes)"
    )
    animation: str = Field(
        default="pop_in",
        description="Entrance animation: pop_in, slide_down_and_bounce, shake, spring, fade",
    )
    keyframes: list[Keyframe] = Field(
        default_factory=list,
        description="Per-property animation keyframes",
    )
    paired_sfx: str | None = Field(
        default=None,
        description="SFX URI to play simultaneously (e.g. vine boom with thug life glasses)",
    )


class SFXInsert(BaseModel):
    """A sound effect placed at a specific moment.

    SFX are timed to VLM edit signals (vine boom on awkward_pause,
    airhorn on punchline, whoosh on transitions). Volume and pitch
    can be adjusted for comedic effect.
    """

    type: str = Field(
        default="sound_effect", description="Insert type identifier"
    )
    at_ms: int = Field(
        ge=0, description="Placement timestamp in clip timeline"
    )
    sfx_uri: str = Field(description="URI of the SFX audio file")
    volume: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Playback volume"
    )
    name: str = Field(
        description="Human-readable SFX name: vine_boom, bruh, whoosh, airhorn"
    )
    pitch_shift: float = Field(
        default=0.0,
        description="Pitch shift in semitones (positive=higher, for comedic effect)",
    )


class MemeLayer(BaseModel):
    """Complete meme/SFX layer for a single clip.

    Produced by the Meme/SFX Agent. Contains all meme overlays and
    sound effects to be applied to a clip. The Assembly Agent merges
    these into the TimelineJSON at z-indices 5-10.
    """

    clip_id: str = Field(description="Target clip identifier")
    inserts: list[MemeInsert | SFXInsert] = Field(
        default_factory=list,
        description="All meme and SFX inserts for this clip",
    )

    @property
    def meme_inserts(self) -> list[MemeInsert]:
        """Filter to only image overlay inserts."""
        return [i for i in self.inserts if isinstance(i, MemeInsert)]

    @property
    def sfx_inserts(self) -> list[SFXInsert]:
        """Filter to only sound effect inserts."""
        return [i for i in self.inserts if isinstance(i, SFXInsert)]

    @property
    def total_sfx_count(self) -> int:
        return len(self.sfx_inserts)

    @property
    def total_meme_count(self) -> int:
        return len(self.meme_inserts)
