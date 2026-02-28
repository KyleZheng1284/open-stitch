"""Subtitle Agent — generates kinetic subtitle layers.

Runs in parallel with Music and Meme/SFX agents on independent z-index
ranges (z=2-4). Reads word-level transcript timings and applies style
presets to generate ASS-format subtitles and Remotion subtitle layers.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas import ProjectRequest
from autovid.schemas.composition import RemotionComposition
from autovid.schemas.transcript import Transcript

from .remotion_tools import remotion_add_subtitle

logger = logging.getLogger(__name__)


class SubtitleAgent:
    """Generates and adds subtitle layers to the composition."""

    async def run(
        self,
        composition: RemotionComposition,
        chunks: list[Any],
        project: ProjectRequest,
    ) -> None:
        """Generate subtitle tracks for all sequences in the composition."""
        languages = project.preferences.subtitle_languages
        style = project.preferences.subtitle_style.value

        logger.info(
            "Subtitle agent: generating %s subtitles in style '%s'",
            languages, style,
        )

        for seq in composition.sequences:
            # TODO: Extract transcript words for this sequence's time range
            # TODO: Generate word-level subtitle blocks
            # TODO: Apply kinetic typography presets
            # TODO: Call remotion_add_subtitle for each subtitle block
            pass

        logger.info("Subtitle agent complete: %d subtitle layers", len(composition.subtitles))

    async def generate_subtitle_track(
        self,
        transcript: Transcript,
        start_ms: int,
        end_ms: int,
        language: str,
        style_preset: str,
    ) -> list[dict[str, Any]]:
        """Generate subtitle blocks for a time range.

        Returns a list of subtitle entries with text, timing, and word-level
        keyframes for kinetic typography rendering.
        """
        words = transcript.words_in_range(start_ms, end_ms)
        if not words:
            return []

        # Group words into subtitle blocks (~4-6 words per block)
        blocks: list[dict[str, Any]] = []
        block_words: list[Any] = []
        block_start = words[0].start_ms

        for word in words:
            block_words.append(word)
            if len(block_words) >= 5 or word is words[-1]:
                blocks.append({
                    "text": " ".join(w.text for w in block_words),
                    "start_ms": block_start,
                    "end_ms": block_words[-1].end_ms,
                    "style_preset": style_preset,
                    "word_timings": [
                        {
                            "text": w.text,
                            "start_ms": w.start_ms,
                            "end_ms": w.end_ms,
                        }
                        for w in block_words
                    ],
                })
                block_words = []
                if word is not words[-1]:
                    next_idx = words.index(word) + 1
                    if next_idx < len(words):
                        block_start = words[next_idx].start_ms

        return blocks

    @staticmethod
    def shorten_for_platform(text: str, platform: str, max_chars: int = 100) -> str:
        """Trim subtitle text for platform character limits."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."
