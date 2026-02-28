"""Timeline JSON schemas for Assembly Agent -> Remotion rendering.

TimelineJSON is the serialized form of RemotionComposition. It maps 1:1
to Remotion <Composition> component props. The Assembly Agent validates
the composition, resolves asset URIs, and serializes to this format before
writing to the sandbox for rendering.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .composition import RemotionComposition


class TimelineOutput(BaseModel):
    """Output format configuration for the rendered clip."""

    format: str = Field(default="mp4")
    codec: str = Field(default="h264")
    width: int = Field(default=1080, gt=0)
    height: int = Field(default=1920, gt=0)
    fps: int = Field(default=30, gt=0)


class TimelineLayer(BaseModel):
    """A single layer in the timeline, generic across all layer types.

    This is the flat serialization format that Remotion reads as props.
    Each layer carries its type, z_index, and type-specific properties.
    """

    type: str = Field(
        description="Layer type: video, meme_overlay, subtitle, subtitle_track, audio, transition"
    )
    z_index: int = Field(description="Stacking order for rendering")

    # Video layer fields
    source: str | None = Field(default=None, description="Asset URI")
    start_ms: int | None = Field(default=None)
    end_ms: int | None = Field(default=None)
    crop: dict[str, float] | None = Field(default=None)
    speed: float | None = Field(default=None)
    transition_in: dict[str, object] | None = Field(default=None)

    # Overlay layer fields
    at_ms: int | None = Field(default=None, description="Start time for overlays/SFX")
    duration_ms: int | None = Field(default=None)
    position: dict[str, float] | tuple[float, float] | str | None = Field(default=None)
    scale: float | None = Field(default=None)
    rotation: float | None = Field(default=None)
    opacity: float | None = Field(default=None)
    animation: str | None = Field(default=None)
    keyframes: list[dict[str, object]] | None = Field(default=None)
    sound_effect: str | None = Field(
        default=None, description="Paired SFX URI for overlay layers"
    )

    # Subtitle layer fields
    text: str | None = Field(default=None)
    style: str | dict[str, object] | None = Field(default=None)

    # Audio layer fields
    volume: float | None = Field(default=None)
    duck_points: list[dict[str, object]] | None = Field(default=None)
    fade_in_ms: int | None = Field(default=None)
    fade_out_ms: int | None = Field(default=None)
    pitch_shift: float | None = Field(default=None)


class TimelineJSON(BaseModel):
    """Complete timeline specification for Remotion rendering.

    This is the final serialized form written to the sandbox at
    /workspace/intermediate/timeline/clip_N.json. The Remotion
    TimelineComposition component reads this JSON as props and renders
    each layer as a React component sorted by z_index.
    """

    clip_id: str
    output: TimelineOutput = Field(default_factory=TimelineOutput)
    layers: list[TimelineLayer] = Field(default_factory=list)

    @classmethod
    def from_composition(cls, comp: RemotionComposition) -> TimelineJSON:
        """Convert a RemotionComposition to the flat TimelineJSON format.

        This is the primary serialization path: the in-memory composition
        (built incrementally by agents) is converted to the JSON format
        that Remotion can render.
        """
        layers: list[TimelineLayer] = []

        # Video sequences -> video layers
        for seq in comp.sequences:
            layers.append(
                TimelineLayer(
                    type="video",
                    z_index=seq.z_index,
                    source=seq.chunk_uri,
                    start_ms=seq.position_in_timeline_ms,
                    end_ms=seq.position_in_timeline_ms + seq.output_duration_ms,
                    crop=seq.crop,
                    speed=seq.speed,
                    transition_in=seq.transition_in,
                )
            )

        # Overlays -> meme_overlay layers
        for ov in comp.overlays:
            layers.append(
                TimelineLayer(
                    type="meme_overlay",
                    z_index=ov.z_index,
                    source=ov.asset_uri,
                    at_ms=ov.at_ms,
                    duration_ms=ov.duration_ms,
                    position={"x": ov.x, "y": ov.y},
                    scale=ov.scale,
                    rotation=ov.rotation,
                    opacity=ov.opacity,
                    animation=ov.animation,
                    keyframes=[kf.model_dump(exclude_none=True) for kf in ov.keyframes],
                    sound_effect=ov.paired_sfx,
                )
            )

        # Subtitles -> subtitle layers
        for sub in comp.subtitles:
            layers.append(
                TimelineLayer(
                    type="subtitle",
                    z_index=sub.z_index,
                    text=sub.text,
                    start_ms=sub.start_ms,
                    end_ms=sub.end_ms,
                    style=sub.style_preset,
                    position=sub.position,
                    keyframes=[kf.model_dump(exclude_none=True) for kf in sub.keyframes],
                )
            )

        # Audio -> audio layers
        for audio in comp.audio_layers:
            layers.append(
                TimelineLayer(
                    type="audio",
                    z_index=audio.z_index,
                    source=audio.audio_uri,
                    at_ms=audio.start_ms,
                    volume=audio.volume,
                    duck_points=audio.duck_points,
                    fade_in_ms=audio.fade_in_ms,
                    fade_out_ms=audio.fade_out_ms,
                    pitch_shift=audio.pitch_shift,
                )
            )

        # Sort by z_index for rendering order
        layers.sort(key=lambda l: l.z_index)

        return cls(
            clip_id=comp.clip_id,
            output=TimelineOutput(
                codec=comp.codec,
                width=comp.width,
                height=comp.height,
                fps=comp.fps,
            ),
            layers=layers,
        )

    @property
    def video_layers(self) -> list[TimelineLayer]:
        return [l for l in self.layers if l.type == "video"]

    @property
    def overlay_layers(self) -> list[TimelineLayer]:
        return [l for l in self.layers if l.type == "meme_overlay"]

    @property
    def subtitle_layers(self) -> list[TimelineLayer]:
        return [l for l in self.layers if l.type in ("subtitle", "subtitle_track")]

    @property
    def audio_layers(self) -> list[TimelineLayer]:
        return [l for l in self.layers if l.type == "audio"]

    @property
    def total_duration_ms(self) -> int:
        """Estimate total duration from video layers."""
        if not self.video_layers:
            return 0
        return max(
            (l.end_ms or 0) for l in self.video_layers
        )
