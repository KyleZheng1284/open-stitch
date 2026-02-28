"""Remotion composition state schemas.

The RemotionComposition is the in-memory accumulator that agents build
incrementally during Phase 2. Each Remotion tool call (remotion_add_sequence,
remotion_add_overlay, etc.) appends to this state. The composition is
thread-safe because Subtitle, Music, and Meme agents write to it in parallel
on independent z-index ranges.

After all agents complete, the Assembly Agent serializes this to TimelineJSON
for sandbox rendering.
"""
from __future__ import annotations

import threading
from uuid import uuid4

from pydantic import BaseModel, Field

from .clip_spec import Keyframe


class RemotionSequence(BaseModel):
    """A base video segment in the composition (z=0).

    Maps to Remotion <Sequence> + <OffthreadVideo>.
    Each sequence is a trimmed, speed-adjusted clip segment.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    chunk_uri: str = Field(description="URI of the source chunk video")
    start_ms: int = Field(ge=0, description="Source start time")
    end_ms: int = Field(ge=0, description="Source end time")
    speed: float = Field(default=1.0, gt=0.0)
    position_in_timeline_ms: int = Field(
        ge=0, description="Where this sequence starts in the output timeline"
    )
    crop: dict[str, float] | None = Field(
        default=None, description="Crop region: x, y, width, height (normalized)"
    )
    z_index: int = Field(default=0)
    transition_in: dict[str, object] | None = Field(
        default=None, description="Incoming transition: type, duration_ms"
    )

    @property
    def source_duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def output_duration_ms(self) -> int:
        return int(self.source_duration_ms / self.speed)


class RemotionOverlay(BaseModel):
    """A visual overlay layer (meme, emoji, text, GIF).

    Maps to Remotion <Img> or <AbsoluteFill> with absolute positioning.
    Position, scale, rotation, and opacity can be animated via keyframes
    using Remotion's interpolate() + spring() functions.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    asset_uri: str = Field(description="URI of the overlay asset")
    at_ms: int = Field(ge=0, description="Start time in output timeline")
    duration_ms: int = Field(gt=0)
    x: float = Field(ge=0.0, le=1.0, description="Horizontal position, normalized")
    y: float = Field(ge=0.0, le=1.0, description="Vertical position, normalized")
    scale: float = Field(default=1.0, gt=0.0)
    rotation: float = Field(default=0.0, description="Degrees")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    z_index: int = Field(default=10, ge=0)
    animation: str = Field(default="none")
    keyframes: list[Keyframe] = Field(default_factory=list)
    paired_sfx: str | None = Field(
        default=None, description="SFX URI to play at at_ms"
    )


class RemotionSubtitle(BaseModel):
    """A subtitle layer in the composition.

    Maps to Remotion <KineticSubtitle> component with per-word animation.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    style_preset: str = Field(default="tiktok_pop")
    position: str = Field(
        default="center_bottom",
        description="Placement: center_bottom, center, top",
    )
    z_index: int = Field(default=5)
    keyframes: list[Keyframe] = Field(default_factory=list)
    word_timings: list[dict[str, object]] = Field(
        default_factory=list,
        description="Per-word timing for kinetic typography",
    )


class RemotionAudio(BaseModel):
    """An audio layer (background music or SFX).

    Audio layers are rendered separately by FFmpeg post-Remotion, since
    FFmpeg's audio mixing (ducking, SFX placement, pitch shift) is more
    capable than Remotion's audio support.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    audio_uri: str = Field(description="URI of the audio file")
    start_ms: int = Field(default=0, ge=0, description="Start time in timeline")
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    duck_points: list[dict[str, object]] = Field(
        default_factory=list,
        description="Volume ducking ranges for speech segments",
    )
    pitch_shift: float = Field(
        default=0.0, description="Pitch shift in semitones"
    )
    fade_in_ms: int = Field(default=0, ge=0)
    fade_out_ms: int = Field(default=0, ge=0)
    z_index: int = Field(default=-1, description="Audio is always z=-1")


class RemotionComposition(BaseModel):
    """Thread-safe in-memory composition state.

    This is the central accumulator that all editing agents write to.
    Each Remotion tool call appends a layer here. The composition is
    organized by layer type and z-index:

    - z=0: Video sequences (base footage)
    - z=1: Transitions (between sequences)
    - z=2-4: Subtitles (kinetic typography)
    - z=5-10: Overlays (memes, emojis, text)
    - z=-1: Audio (music, SFX -- mixed by FFmpeg)

    Thread safety: Subtitle, Music, and Meme agents run in parallel but
    write to independent z-index ranges, so there are no conflicts. The
    lock protects against concurrent list mutations.
    """

    clip_id: str = Field(default_factory=lambda: str(uuid4()))
    width: int = Field(default=1080)
    height: int = Field(default=1920)
    fps: int = Field(default=30)
    codec: str = Field(default="h264")

    sequences: list[RemotionSequence] = Field(default_factory=list)
    overlays: list[RemotionOverlay] = Field(default_factory=list)
    subtitles: list[RemotionSubtitle] = Field(default_factory=list)
    audio_layers: list[RemotionAudio] = Field(default_factory=list)

    # Thread lock for concurrent agent writes -- excluded from serialization
    _lock: threading.Lock | None = None

    def model_post_init(self, __context: object) -> None:
        object.__setattr__(self, "_lock", threading.Lock())

    @property
    def lock(self) -> threading.Lock:
        if self._lock is None:
            object.__setattr__(self, "_lock", threading.Lock())
        return self._lock

    def add_sequence(self, sequence: RemotionSequence) -> None:
        """Thread-safe append of a video sequence."""
        with self.lock:
            self.sequences.append(sequence)

    def add_overlay(self, overlay: RemotionOverlay) -> None:
        """Thread-safe append of a visual overlay."""
        with self.lock:
            self.overlays.append(overlay)

    def add_subtitle(self, subtitle: RemotionSubtitle) -> None:
        """Thread-safe append of a subtitle layer."""
        with self.lock:
            self.subtitles.append(subtitle)

    def add_audio(self, audio: RemotionAudio) -> None:
        """Thread-safe append of an audio layer."""
        with self.lock:
            self.audio_layers.append(audio)

    def remove_layer(self, layer_id: str) -> bool:
        """Remove a layer by ID from any category. Returns True if found."""
        with self.lock:
            for collection in [
                self.sequences,
                self.overlays,
                self.subtitles,
                self.audio_layers,
            ]:
                for i, layer in enumerate(collection):
                    if layer.id == layer_id:
                        collection.pop(i)
                        return True
        return False

    @property
    def total_duration_ms(self) -> int:
        """Estimated total duration based on sequence positions and durations."""
        if not self.sequences:
            return 0
        return max(
            s.position_in_timeline_ms + s.output_duration_ms
            for s in self.sequences
        )

    @property
    def layer_count(self) -> int:
        """Total number of layers across all categories."""
        return (
            len(self.sequences)
            + len(self.overlays)
            + len(self.subtitles)
            + len(self.audio_layers)
        )

    def all_layers_sorted(self) -> list[BaseModel]:
        """All layers sorted by z_index for rendering order."""
        all_layers: list[BaseModel] = [
            *self.sequences,
            *self.overlays,
            *self.subtitles,
            *self.audio_layers,
        ]
        return sorted(all_layers, key=lambda l: getattr(l, "z_index", 0))
