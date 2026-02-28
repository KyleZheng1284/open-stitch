"""Clip specification schemas for the ReAct planner output.

ClipSpec is the core output of the ReAct Reasoning Loop. It defines exactly
how a final clip should be assembled: which segments to include, transitions,
overlays, subtitle config, music mood, and meme placement points.

The Assembly Agent consumes ClipSpec to build the TimelineJSON.
"""
from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from .project import Platform, SubtitleStyle


class Keyframe(BaseModel):
    """Animation keyframe for overlay/subtitle micro-animations.

    Maps to Remotion interpolate() + spring() calls. Supports TikTok-style
    entrance animations (pop-in, bounce, shake) and smooth property
    transitions over time.
    """

    time_ms: int = Field(
        ge=0, description="Timestamp relative to the overlay/subtitle start"
    )
    x: float | None = Field(
        default=None, description="Normalized position override"
    )
    y: float | None = Field(
        default=None, description="Normalized position override"
    )
    scale: float | None = Field(
        default=None, description="Scale factor override"
    )
    rotation: float | None = Field(
        default=None, description="Rotation in degrees override"
    )
    opacity: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Opacity override"
    )
    easing: str = Field(
        default="linear",
        description="Easing function: linear, ease_in, ease_out, spring, bounce",
    )


class ZoomSpec(BaseModel):
    """Zoom configuration for a video segment.

    center_x/center_y define the focal point (from VLM subject tracking).
    Used by Remotion to render a smooth Ken Burns zoom effect.
    """

    center_x: float = Field(ge=0.0, le=1.0, description="Zoom center X, normalized")
    center_y: float = Field(ge=0.0, le=1.0, description="Zoom center Y, normalized")
    scale: float = Field(
        gt=0.0, description="Zoom level: 1.0=no zoom, 2.0=2x magnification"
    )


class CropSpec(BaseModel):
    """Crop region for aspect ratio conversion or subject framing."""

    x: float = Field(ge=0.0, le=1.0, description="Left edge, normalized")
    y: float = Field(ge=0.0, le=1.0, description="Top edge, normalized")
    width: float = Field(gt=0.0, le=1.0, description="Crop width, normalized")
    height: float = Field(gt=0.0, le=1.0, description="Crop height, normalized")


class EditSegment(BaseModel):
    """A single video segment within a clip.

    Each segment references a chunk and defines the time range to extract,
    playback speed, and optional zoom effect. Segments are ordered
    chronologically in the ClipSpec.segments list.
    """

    chunk_id: str = Field(description="Source chunk identifier")
    start_ms: int = Field(ge=0, description="Start time within the chunk (ms)")
    end_ms: int = Field(ge=0, description="End time within the chunk (ms)")
    speed: float = Field(
        default=1.0, gt=0.0, le=4.0, description="Playback speed multiplier"
    )
    zoom: ZoomSpec | None = Field(
        default=None, description="Optional zoom effect for this segment"
    )

    @property
    def source_duration_ms(self) -> int:
        """Duration of the source footage before speed adjustment."""
        return self.end_ms - self.start_ms

    @property
    def output_duration_ms(self) -> int:
        """Duration after speed adjustment."""
        return int(self.source_duration_ms / self.speed)


class HookSpec(BaseModel):
    """Hook text overlay at the start of a clip.

    Hooks grab viewer attention in the first 1-3 seconds.
    The ReAct agent generates hook text based on clip content.
    """

    text: str = Field(description="Hook text, e.g. 'WAIT FOR IT...'")
    duration_ms: int = Field(
        default=3000, gt=0, description="How long the hook stays on screen"
    )
    style: str = Field(
        default="bold_center",
        description="Rendering style: bold_center, top_bar, animated_type",
    )


class OutroSpec(BaseModel):
    """Outro card at the end of a clip."""

    text: str = Field(description="Outro text, e.g. 'Follow for more!'")
    duration_ms: int = Field(default=2000, gt=0)
    style: str = Field(default="fade_card")


class TransitionSpec(BaseModel):
    """Transition effect between two segments.

    Maps to Remotion <TransitionEffect> component.
    """

    type: str = Field(
        description="Transition type: cut, crossfade, swipe_left, swipe_right, zoom_in, glitch"
    )
    between_segments: tuple[int, int] = Field(
        description="Indices of the two segments this transition connects"
    )
    duration_ms: int = Field(
        default=500, gt=0, le=2000, description="Transition duration"
    )


class MemePoint(BaseModel):
    """A flagged moment where a meme/SFX should be inserted.

    The ReAct agent identifies these from VLM edit signals. The Meme/SFX
    Agent uses these as placement targets, selecting specific assets and
    positioning from the VLM bounding box data.
    """

    at_ms: int = Field(
        ge=0, description="Timestamp in the assembled clip timeline"
    )
    context: str = Field(
        description="Why a meme fits here, e.g. 'awkward pause after joke'"
    )
    suggested_type: str = Field(
        description="Suggested meme type: sound_effect, image_overlay, both"
    )
    mood: str = Field(
        description="Meme mood: funny, dramatic, hype, cringe"
    )


class SubtitleConfig(BaseModel):
    """Subtitle generation configuration for a clip."""

    languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="ISO 639-1 language codes",
    )
    style_preset: SubtitleStyle = Field(
        default=SubtitleStyle.TIKTOK_POP,
        description="Rendering style from config/subtitle_styles.yaml",
    )
    burn_in: bool = Field(
        default=True,
        description="Whether to burn subtitles into the video vs. separate file",
    )


class OverlaySpec(BaseModel):
    """A visual overlay (meme image, emoji, text, GIF) placed on the clip.

    Position coordinates come from VLM spatial grounding (subject bounding
    boxes). Animation keyframes enable TikTok-style micro-animations.
    """

    type: str = Field(
        description="Overlay type: emoji, text, image, meme_image, gif"
    )
    content: str = Field(description="Asset URI or text content")
    position: tuple[float, float] = Field(
        description="(x, y) normalized 0.0-1.0 placement"
    )
    start_ms: int = Field(ge=0, description="Overlay start time in clip timeline")
    end_ms: int = Field(ge=0, description="Overlay end time in clip timeline")
    scale: float = Field(default=1.0, gt=0.0, description="Scale factor")
    rotation: float = Field(default=0.0, description="Rotation in degrees")
    opacity: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Opacity 0.0-1.0"
    )
    z_index: int = Field(
        default=10, ge=0, description="Z-axis stacking order (higher = on top)"
    )
    animation: str = Field(
        default="none",
        description="Entrance animation: none, pop_in, slide_down_and_bounce, shake, fade, spring",
    )
    keyframes: list[Keyframe] = Field(
        default_factory=list,
        description="Fine-grained per-property animation control",
    )
    paired_sfx: str | None = Field(
        default=None,
        description="Optional SFX URI to play at start_ms (e.g. vine boom with meme)",
    )


class ClipSpec(BaseModel):
    """Complete specification for a single output clip.

    This is the core output of the ReAct Reasoning Loop. Every field
    directly maps to a rendering decision. The Assembly Agent validates
    this spec and converts it to TimelineJSON for Remotion rendering.
    """

    clip_id: str = Field(default_factory=lambda: str(uuid4()))
    source_chunks: list[str] = Field(
        min_length=1,
        description="Chunk IDs that contribute footage to this clip",
    )
    segments: list[EditSegment] = Field(
        min_length=1,
        description="Ordered list of video segments to include",
    )
    aspect_ratio: str = Field(default="9:16")
    crop: CropSpec | None = None
    hook: HookSpec | None = None
    outro: OutroSpec | None = None
    subtitle_config: SubtitleConfig = Field(default_factory=SubtitleConfig)
    transitions: list[TransitionSpec] = Field(default_factory=list)
    meme_points: list[MemePoint] = Field(
        default_factory=list,
        description="Flagged moments for meme/SFX insertion",
    )
    music_mood_tags: list[str] = Field(
        default_factory=list,
        description="Music mood tags: chill, lo-fi, upbeat, dramatic",
    )
    music_energy_curve: str = Field(
        default="match_content",
        description="Energy curve: match_content, flat, build_up, drop",
    )
    overlays: list[OverlaySpec] = Field(
        default_factory=list,
        description="Pre-placed visual overlays from ReAct loop",
    )
    platform: Platform = Field(default=Platform.YOUTUBE_SHORTS)
    title: str = Field(default="", description="Clip title for publishing")
    description: str = Field(
        default="", description="Clip description for publishing"
    )
    tags: list[str] = Field(default_factory=list)

    @property
    def total_source_duration_ms(self) -> int:
        """Sum of all segment durations before speed adjustment."""
        return sum(s.source_duration_ms for s in self.segments)

    @property
    def estimated_output_duration_ms(self) -> int:
        """Estimated output duration accounting for speed adjustments."""
        base = sum(s.output_duration_ms for s in self.segments)
        hook_dur = self.hook.duration_ms if self.hook else 0
        outro_dur = self.outro.duration_ms if self.outro else 0
        return base + hook_dur + outro_dur
