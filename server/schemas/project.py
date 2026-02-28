"""Project and job schemas."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VideoLength(str, Enum):
    SHORT = "short"  # 15-60s
    LONG = "long"    # 1-10min


class VideoStyle(str, Enum):
    VLOG = "vlog"
    TUTORIAL = "tutorial"
    HIGHLIGHTS = "highlights"
    STORY = "story"
    CINEMATIC = "cinematic"


class ProjectCreate(BaseModel):
    video_ids: list[str] = Field(..., description="Ordered list of Drive video IDs")
    video_order: list[str] | None = None


class ClarifyAnswer(BaseModel):
    answers: dict[str, str] = Field(..., description="Question ID → answer text")


class EditRequest(BaseModel):
    structured_prompt: str = Field(..., description="Full structured prompt from clarifying agent")


class VideoInfo(BaseModel):
    id: str
    filename: str
    local_path: str = ""
    duration_s: float = 0
    width: int = 0
    height: int = 0
    summary: str = ""
    ingestion_status: str = "pending"


class ProjectStatus(BaseModel):
    id: str
    status: str
    videos: list[VideoInfo] = []
    output_uri: str | None = None
    error: str | None = None
