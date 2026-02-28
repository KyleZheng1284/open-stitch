"""Project-level schemas for API requests and responses.

These schemas define the top-level data structures for creating editing
projects, configuring preferences, and receiving pipeline results.
"""
from __future__ import annotations

from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Target social publishing platform."""

    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE_LONG = "youtube_long"


class SubtitleStyle(str, Enum):
    """Subtitle rendering style presets.

    Maps to ASS format templates in config/subtitle_styles.yaml.
    """

    TIKTOK_POP = "tiktok_pop"
    MINIMAL = "minimal"
    KARAOKE = "karaoke"
    OUTLINE = "outline"


class EditPreferences(BaseModel):
    """User preferences that control the editing pipeline behavior.

    These are set once per project and injected into every agent's context.
    The ReAct loop reads these to constrain its clip planning.
    """

    clip_count: int = Field(
        default=5, ge=1, le=20, description="Target number of clips to produce"
    )
    clip_length_range: tuple[int, int] = Field(
        default=(15, 60),
        description="Min/max clip duration in seconds",
    )
    subtitle_languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="ISO 639-1 language codes for subtitle generation",
    )
    subtitle_style: SubtitleStyle = Field(
        default=SubtitleStyle.TIKTOK_POP,
        description="Subtitle rendering preset",
    )
    aspect_ratio: str = Field(
        default="9:16", description="Output aspect ratio: 9:16, 16:9, 1:1"
    )
    include_hooks: bool = Field(
        default=True, description="Generate hook text overlays at clip start"
    )
    include_memes: bool = Field(
        default=True, description="Enable meme image/GIF overlays"
    )
    include_background_music: bool = Field(
        default=True, description="Add background music tracks"
    )
    include_sfx: bool = Field(
        default=True, description="Add sound effects at meme/transition points"
    )
    include_compilation: bool = Field(
        default=False, description="Also produce a long-form compilation"
    )
    music_mood: str | None = Field(
        default=None,
        description="Override music mood; if None, derived from style_prompt",
    )


class ProjectRequest(BaseModel):
    """Top-level request to create an editing project.

    Submitted via POST /api/v1/projects. The video_uris trigger
    immediate async ingestion (Phase 1). The style_prompt and preferences
    are used when the user submits the edit job (Phase 2).
    """

    project_id: str = Field(default_factory=lambda: str(uuid4()))
    video_uris: list[str] = Field(
        min_length=1,
        description="Object store URIs of uploaded raw videos",
    )
    creator_id: str | None = Field(
        default=None, description="User identifier for multi-tenancy"
    )
    style_prompt: str = Field(
        description="Free-text style/vibe description driving all agent decisions"
    )
    preferences: EditPreferences = Field(default_factory=EditPreferences)
    target_platforms: list[Platform] = Field(
        default_factory=lambda: [Platform.YOUTUBE_SHORTS],
        description="Platforms to publish to",
    )


class ProjectResult(BaseModel):
    """Final output of a completed editing pipeline run.

    Returned from the Director Agent after all clips are rendered
    and optionally published.
    """

    project_id: str
    job_id: str
    clip_uris: list[str] = Field(
        description="Object store URIs of rendered clips"
    )
    subtitle_uris: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of clip_id -> list of subtitle file URIs",
    )
    thumbnail_uris: list[str] = Field(
        default_factory=list,
        description="Generated thumbnail URIs per clip",
    )
    compilation_uri: str | None = Field(
        default=None, description="URI of long-form compilation if requested"
    )
    publish_results: list[dict[str, str]] = Field(
        default_factory=list,
        description="Per-platform publish status with share URLs",
    )
    total_duration_s: float = Field(
        default=0.0, description="Total pipeline execution time in seconds"
    )
    total_tokens: int = Field(
        default=0, description="Total LLM/VLM tokens consumed"
    )
