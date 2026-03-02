"""Video and ingestion data schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DriveFile(BaseModel):
    id: str
    name: str
    mime_type: str = ""
    size_bytes: int = 0
    thumbnail_url: str = ""
    duration_s: float = 0


class WordSegment(BaseModel):
    word: str
    start: float
    end: float
    confidence: float = 1.0


class ASRResult(BaseModel):
    words: list[WordSegment] = []
    sentences: list[dict] = []
    language: str = "en"


class VLMSecond(BaseModel):
    t: float
    action: str = ""
    energy: float = 0.0
    edit_signal: str = "hold"
    subjects: list[dict] = []
    motion: dict = {}
    face: dict = {}
    meme_potential: float = 0.0


class VLMWindow(BaseModel):
    seconds: list[VLMSecond] = []
    window_summary: str = ""
    peak_moment: float = 0.0


class TimelineEntry(BaseModel):
    t: int
    action: str = ""
    energy: float = 0.0
    edit_signal: str = "hold"
    speech: str = ""
    word_count: int = 0
    avg_confidence: float = 0.0
    subjects: list[dict] = []
    face: dict = {}
    motion: dict = {}
    meme_potential: float = 0.0


class IngestedVideo(BaseModel):
    video_id: str
    local_path: str
    duration_s: float
    summary: str = ""
    asr: ASRResult = ASRResult()
    vlm_windows: list[VLMWindow] = []
    timeline: list[TimelineEntry] = []
