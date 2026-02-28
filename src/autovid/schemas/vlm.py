"""VLM (Vision-Language Model) output schemas.

These schemas represent the dense per-second analysis produced by the VLM
during Phase 1 ingestion. The primary model is Qwen3.5-397B-A17B with native
video token input. Every schema here maps directly to the structured JSON
output defined in the VLM system prompt (config/prompts/vlm_edit_grade.txt).

The editing agents in Phase 2 consume these schemas to make cut, overlay,
transition, subtitle, and music decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator


@dataclass(frozen=True, slots=True)
class FrameAnalysis:
    """Legacy per-frame analysis. Used for on-demand follow-up VLM queries.

    The ReAct agent calls describe_frame() when it needs more detail about
    a specific moment beyond what the chunk-level analysis provides.
    """

    caption: str
    tags: list[str] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    emotion: str | None = None
    energy_score: float = 0.0


class BoundingBox(BaseModel):
    """Normalized bounding box for spatial grounding.

    All coordinates are 0.0-1.0, relative to frame dimensions.
    Used for meme placement, zoom targeting, and subject tracking.
    """

    x: float = Field(ge=0.0, le=1.0, description="Left edge, normalized")
    y: float = Field(ge=0.0, le=1.0, description="Top edge, normalized")
    width: float = Field(ge=0.0, le=1.0, description="Width, normalized")
    height: float = Field(ge=0.0, le=1.0, description="Height, normalized")

    @property
    def center(self) -> tuple[float, float]:
        """Center point of the bounding box."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> float:
        """Normalized area (0.0-1.0)."""
        return self.width * self.height

    def contains_point(self, px: float, py: float) -> bool:
        """Check if a point falls within this bounding box."""
        return (
            self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height
        )


class SubjectPosition(BaseModel):
    """A tracked subject within a frame with spatial and emotional metadata.

    The VLM identifies subjects per-second and provides bounding boxes
    that downstream agents use for:
    - Meme overlay placement (glasses on face, hat on head)
    - Zoom/crop centering on speaker
    - Subtitle positioning relative to speaker
    """

    label: str = Field(
        description="Subject identifier: person_1, laptop, whiteboard, hand, etc."
    )
    bbox: BoundingBox
    face_emotion: str | None = Field(
        default=None,
        description="Detected emotion: laughing, surprised, focused, bored, confused, smiling, neutral",
    )
    is_speaking: bool = False


class SceneComposition(BaseModel):
    """Visual composition metadata for a frame.

    Used by the ReAct agent to make framing decisions (e.g., close-up shots
    get different treatment than wide shots) and by the Assembly Agent to
    validate that crop/zoom operations make sense.
    """

    framing: str = Field(
        description="Shot type: close_up, medium, wide, extreme_close_up, over_shoulder"
    )
    lighting: str = Field(
        description="Lighting condition: bright, dim, backlit, neon, natural, mixed"
    )
    background: str = Field(description="Brief background description")
    visual_complexity: float = Field(
        ge=0.0,
        le=1.0,
        description="Frame complexity: 0.0=clean, 1.0=cluttered",
    )


class SecondAnalysis(BaseModel):
    """Dense per-second analysis. One entry per second of video chunk.

    This is the core unit of information the editing agents consume.
    Every field directly informs an editing decision:
    - edit_signal -> where to cut, what to keep, where to add effects
    - subjects -> where to place overlays (bounding box coordinates)
    - energy -> pacing and transition decisions
    - emotion -> music mood matching and SFX selection
    """

    second: int = Field(ge=0, description="0-indexed second within chunk")
    timestamp_ms: int = Field(
        ge=0, description="Absolute ms position in source video"
    )
    visual_description: str = Field(
        description="What is visually happening this second"
    )
    spoken_text: str | None = Field(
        default=None,
        description="Transcript text aligned to this second",
    )
    emotion: str = Field(
        description="Dominant tone: funny, tense, boring, surprising, awkward, hype, calm, emotional"
    )
    energy: float = Field(
        ge=0.0,
        le=1.0,
        description="Combined visual+audio dynamism: 0.0=dead air, 1.0=peak moment",
    )
    edit_signal: str | None = Field(
        default=None,
        description="Edit hint: punchline, cut_point, skip, reaction, energy_shift, dramatic_beat, awkward_pause",
    )
    edit_signal_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in the edit signal"
    )
    edit_signal_reason: str | None = Field(
        default=None,
        description="Brief explanation, e.g. 'joke lands, face shows surprise'",
    )
    subjects: list[SubjectPosition] = Field(default_factory=list)
    scene_composition: SceneComposition | None = None
    camera_movement: str | None = Field(
        default=None,
        description="Camera motion: static, pan_left, pan_right, zoom_in, zoom_out, handheld_shake, tilt, tracking",
    )
    on_screen_text: str | None = Field(
        default=None,
        description="Visible text: signs, laptop screens, captions",
    )

    @field_validator("edit_signal")
    @classmethod
    def validate_edit_signal(cls, v: str | None) -> str | None:
        valid_signals = {
            "punchline",
            "cut_point",
            "skip",
            "reaction",
            "energy_shift",
            "dramatic_beat",
            "awkward_pause",
            None,
        }
        if v not in valid_signals:
            raise ValueError(
                f"Invalid edit_signal '{v}'. Must be one of {valid_signals}"
            )
        return v


class ChunkVLMAnalysis(BaseModel):
    """Dense VLM output for an entire chunk.

    Produced by VLMProvider.analyze_video_chunk() during Phase 1 ingestion.
    Contains one SecondAnalysis per second of video, plus chunk-level editorial
    metadata. This is the primary data structure the editing agents read from
    the ChunkStore.
    """

    chunk_id: str
    seconds: list[SecondAnalysis] = Field(
        description="One entry per second of the chunk"
    )
    summary: str = Field(
        description="2-3 sentence editorial summary of the chunk"
    )
    highlight_seconds: list[int] = Field(
        default_factory=list,
        description="Seconds flagged as edit-worthy (punchline, reaction, energy_shift)",
    )
    skip_ranges: list[tuple[int, int]] = Field(
        default_factory=list,
        description="(start_s, end_s) ranges of dead air / filler",
    )
    dominant_mood: str = Field(
        description="Overall mood: funny, serious, chaotic, chill, dramatic, hype, emotional, awkward"
    )
    narrative_role: str = Field(
        description="Chunk role: intro, buildup, climax, cooldown, filler, transition"
    )
    suggested_speed: float = Field(
        default=1.0,
        description="Suggested playback speed: 1.0=normal, 1.5=fast, 0.8=slow-mo",
    )

    def has_high_energy_second(self, threshold: float = 0.7) -> bool:
        """Check if any second exceeds the energy threshold.

        Used by the Audio Analyzer to decide adaptive FPS for re-analysis:
        high-energy chunks get 4 FPS VLM analysis for finer granularity.
        """
        return any(s.energy >= threshold for s in self.seconds)

    def seconds_with_signal(self, signal: str) -> list[SecondAnalysis]:
        """Filter seconds by edit signal type.

        Used by the ReAct agent to query specific moment types:
        e.g., 'give me all punchlines', 'find all reaction moments'.
        """
        return [s for s in self.seconds if s.edit_signal == signal]

    def peak_energy_second(self) -> SecondAnalysis | None:
        """Return the highest-energy second in the chunk."""
        if not self.seconds:
            return None
        return max(self.seconds, key=lambda s: s.energy)

    def subjects_at_second(self, second: int) -> list[SubjectPosition]:
        """Get all tracked subjects at a specific second."""
        for s in self.seconds:
            if s.second == second:
                return s.subjects
        return []
