"""Chunk metadata schemas for Phase 1 ingestion output.

ChunkMetadata is the core data structure flowing from Phase 1 (async ingestion)
into Phase 2 (agentic editing). Each video is split into chunks, and each chunk
is independently processed by ASR, VLM, and Audio Analyzer workers.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from .transcript import WordSegment
from .vlm import ChunkVLMAnalysis


class AudioFeatures(BaseModel):
    """Audio analysis results for a single chunk.

    Produced by the Audio Analyzer worker. Used for:
    - Adaptive FPS decisions (high energy -> 4 FPS VLM analysis)
    - Music ducking (silence segments mark non-speech regions)
    - SFX/meme timing (peak timestamps align effects with audio events)
    - Speech rate detection (fast speech -> different subtitle pacing)
    """

    avg_loudness_lufs: float = Field(description="Average loudness in LUFS")
    peak_loudness_lufs: float = Field(description="Peak loudness in LUFS")
    silence_segments: list[tuple[int, int]] = Field(
        default_factory=list,
        description="(start_ms, end_ms) ranges of silence",
    )
    speech_rate_wpm: float | None = Field(
        default=None, description="Words per minute if speech detected"
    )
    has_music: bool = Field(
        default=False, description="Whether background music is detected"
    )
    has_laughter: bool = Field(
        default=False, description="Whether laughter is detected"
    )
    energy_profile: list[float] = Field(
        default_factory=list,
        description="Per-second energy values, 0.0-1.0",
    )
    peak_timestamps_ms: list[int] = Field(
        default_factory=list,
        description="Timestamps of audio peaks for SFX/meme placement",
    )

    def has_high_energy_second(self, threshold: float = 0.7) -> bool:
        """Check if any second in the energy profile exceeds threshold.

        Determines adaptive VLM FPS: True -> 4 FPS, False -> 1 FPS.
        This ensures fast-moving, high-energy content gets finer-grained
        visual analysis from the VLM.
        """
        return any(e >= threshold for e in self.energy_profile)

    def silence_duration_ms(self) -> int:
        """Total duration of silence across all segments."""
        return sum(end - start for start, end in self.silence_segments)

    def peak_in_range(self, start_ms: int, end_ms: int) -> list[int]:
        """Get audio peaks within a time range."""
        return [t for t in self.peak_timestamps_ms if start_ms <= t <= end_ms]


class ChunkMetadata(BaseModel):
    """Complete metadata for a single video chunk after Phase 1 processing.

    This is the primary data structure stored in the ChunkStore and read by
    all Phase 2 agents. It aggregates outputs from three parallel workers:
    ASR (transcript), VLM (dense visual analysis), and Audio Analyzer.
    """

    chunk_id: str = Field(description="Unique chunk identifier")
    video_id: str = Field(description="Parent video identifier")
    project_id: str = Field(description="Parent project identifier")
    chunk_index: int = Field(
        ge=0, description="Position in chronological order within the video"
    )
    start_ms: int = Field(ge=0, description="Start time in source video (ms)")
    end_ms: int = Field(ge=0, description="End time in source video (ms)")
    duration_ms: int = Field(gt=0, description="Chunk duration (ms)")
    video_uri: str = Field(description="URI of chunk video in object store")
    audio_uri: str = Field(description="URI of extracted chunk audio")

    # Phase 1 worker outputs (populated asynchronously)
    transcript: list[WordSegment] | None = Field(
        default=None, description="ASR output: word-level timestamps"
    )
    vlm_analysis: ChunkVLMAnalysis | None = Field(
        default=None, description="Dense per-second VLM analysis"
    )
    audio_features: AudioFeatures | None = Field(
        default=None, description="Audio analysis results"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_fully_processed(self) -> bool:
        """Whether all three Phase 1 workers have completed."""
        return (
            self.transcript is not None
            and self.vlm_analysis is not None
            and self.audio_features is not None
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def processing_status(self) -> str:
        """Human-readable processing status for UI display."""
        done = sum(
            1
            for x in [self.transcript, self.vlm_analysis, self.audio_features]
            if x is not None
        )
        if done == 3:
            return "complete"
        if done == 0:
            return "pending"
        return f"processing ({done}/3)"

    def highlight_seconds(self) -> list[int]:
        """Get edit-worthy seconds from VLM analysis."""
        if self.vlm_analysis is None:
            return []
        return self.vlm_analysis.highlight_seconds

    def should_use_high_fps(self, threshold: float = 0.7) -> bool:
        """Determine if this chunk needs high-FPS VLM re-analysis.

        Based on audio energy. If any second exceeds threshold,
        the VLM should re-analyze at 4 FPS for finer detail.
        """
        if self.audio_features is None:
            return False
        return self.audio_features.has_high_energy_second(threshold)
