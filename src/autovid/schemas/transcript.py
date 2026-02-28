"""Transcript and word-level timing schemas.

Used by ASR workers (Phase 1) and downstream agents for subtitle generation,
speech-aligned meme placement, and music ducking.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WordSegment:
    """A single word with precise timing from ASR output.

    Coordinates are absolute milliseconds in the source video.
    Confidence is model-reported; use for filtering low-quality segments.
    """

    text: str
    start_ms: int
    end_ms: int
    confidence: float
    speaker: str | None = None

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    def overlaps(self, start: int, end: int) -> bool:
        """Check if this word overlaps with a time range."""
        return self.start_ms < end and self.end_ms > start


@dataclass(slots=True)
class Transcript:
    """Full transcript for a video chunk with word-level timing.

    The words list is ordered chronologically. Helper methods provide
    range queries and format conversions needed by downstream agents.
    """

    words: list[WordSegment] = field(default_factory=list)
    language: str = "en"
    source_model: str = "whisper-large-v3-turbo"

    @property
    def full_text(self) -> str:
        """Concatenated transcript text."""
        return " ".join(w.text for w in self.words)

    @property
    def duration_ms(self) -> int:
        """Total span from first word start to last word end."""
        if not self.words:
            return 0
        return self.words[-1].end_ms - self.words[0].start_ms

    def speech_segments(self, gap_threshold_ms: int = 500) -> list[tuple[int, int]]:
        """Return contiguous speech ranges, merging gaps smaller than threshold.

        Used by the Music Agent to generate duck points (lower music volume
        during speech) and by the Meme/SFX Agent to avoid placing SFX over
        speech.

        Returns:
            List of (start_ms, end_ms) tuples for continuous speech regions.
        """
        if not self.words:
            return []

        segments: list[tuple[int, int]] = []
        seg_start = self.words[0].start_ms
        seg_end = self.words[0].end_ms

        for word in self.words[1:]:
            if word.start_ms - seg_end <= gap_threshold_ms:
                seg_end = word.end_ms
            else:
                segments.append((seg_start, seg_end))
                seg_start = word.start_ms
                seg_end = word.end_ms

        segments.append((seg_start, seg_end))
        return segments

    def words_in_range(self, start_ms: int, end_ms: int) -> list[WordSegment]:
        """Get all words overlapping with a time range.

        Used by the Subtitle Agent to extract words for a specific clip segment,
        and by the ReAct loop to cross-reference transcript with VLM analysis.
        """
        return [w for w in self.words if w.overlaps(start_ms, end_ms)]

    def word_timing_for_remotion(
        self, start_ms: int, end_ms: int
    ) -> list[dict[str, object]]:
        """Export word timings as Remotion-compatible props.

        Each word gets a relative offset from segment start, suitable for
        KineticSubtitle component rendering.

        Returns:
            List of dicts with keys: text, startFrame, endFrame, offsetMs.
        """
        fps = 30  # standard Remotion fps
        result: list[dict[str, object]] = []
        for w in self.words_in_range(start_ms, end_ms):
            relative_start = max(0, w.start_ms - start_ms)
            relative_end = min(end_ms - start_ms, w.end_ms - start_ms)
            result.append(
                {
                    "text": w.text,
                    "startFrame": round(relative_start / 1000 * fps),
                    "endFrame": round(relative_end / 1000 * fps),
                    "offsetMs": relative_start,
                }
            )
        return result
