"""Remotion composition schemas for the editing agent."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class Sequence(BaseModel):
    id: str = Field(default_factory=lambda: f"seq_{uuid.uuid4().hex[:8]}")
    source_uri: str
    start_ms: int
    end_ms: int
    position_ms: int = 0
    speed: float = 1.0
    crop: dict | None = None
    transition_in: dict | None = None


class Subtitle(BaseModel):
    id: str = Field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:8]}")
    text: str
    start_ms: int
    end_ms: int
    style: str = "tiktok_pop"
    position: str = "center_bottom"
    word_timings: list[dict] = []


class AudioLayer(BaseModel):
    id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:8]}")
    audio_uri: str
    start_ms: int = 0
    volume: float = 0.8
    duck_points: list[dict] = []
    fade_in_ms: int = 0
    fade_out_ms: int = 0


class Overlay(BaseModel):
    id: str = Field(default_factory=lambda: f"ovl_{uuid.uuid4().hex[:8]}")
    asset_uri: str
    at_ms: int
    duration_ms: int = 2000
    x: float = 0.5
    y: float = 0.5
    scale: float = 1.0
    animation: str = "pop"


class Composition(BaseModel):
    clip_id: str = Field(default_factory=lambda: f"clip_{uuid.uuid4().hex[:8]}")
    width: int = 1080
    height: int = 1920
    fps: int = 30
    sequences: list[Sequence] = []
    subtitles: list[Subtitle] = []
    audio_layers: list[AudioLayer] = []
    overlays: list[Overlay] = []

    def add_sequence(self, **kwargs) -> str:
        seq = Sequence(**kwargs)
        self.sequences.append(seq)
        return seq.id

    def add_subtitle(self, **kwargs) -> str:
        sub = Subtitle(**kwargs)
        self.subtitles.append(sub)
        return sub.id

    def add_audio(self, **kwargs) -> str:
        aud = AudioLayer(**kwargs)
        self.audio_layers.append(aud)
        return aud.id

    def add_overlay(self, **kwargs) -> str:
        ovl = Overlay(**kwargs)
        self.overlays.append(ovl)
        return ovl.id

    @property
    def total_duration_ms(self) -> int:
        if not self.sequences:
            return 0
        return max(s.position_ms + int((s.end_ms - s.start_ms) / s.speed) for s in self.sequences)

    def to_timeline_json(self) -> dict:
        """Serialize to the format expected by sandbox Remotion render."""
        return {
            "clip_id": self.clip_id,
            "output": {"width": self.width, "height": self.height, "fps": self.fps, "codec": "h264"},
            "layers": (
                [{"type": "video", **s.model_dump()} for s in self.sequences]
                + [{"type": "subtitle", **s.model_dump()} for s in self.subtitles]
                + [{"type": "audio", **a.model_dump()} for a in self.audio_layers]
                + [{"type": "overlay", **o.model_dump()} for o in self.overlays]
            ),
        }
