"""ASR Worker — per-chunk speech recognition.

Produces word-level timestamps with speaker labels. Runs as the first
stage of chunk processing (fast: ~2-5s per chunk on GPU).
"""
from __future__ import annotations

import logging

from autovid.schemas.transcript import Transcript, WordSegment

logger = logging.getLogger(__name__)


class ASRWorker:
    """Transcribe audio chunks to word-level timestamps."""

    async def transcribe(
        self,
        audio_uri: str,
        language: str = "auto",
    ) -> Transcript:
        """Transcribe a chunk's audio using the configured ASR provider.

        Returns a Transcript with word-level timing, confidence scores,
        and optional speaker labels.
        """
        logger.info("ASR transcribing: %s (lang=%s)", audio_uri, language)

        # TODO: Load audio from object store
        # TODO: Call ASRProvider.transcribe()
        # TODO: Convert to WordSegment list

        return Transcript(words=[], language=language)
