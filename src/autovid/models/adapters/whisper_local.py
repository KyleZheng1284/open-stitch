"""Whisper Local ASR Adapter.

Runs whisper-large-v3-turbo via faster-whisper for local inference.
809M params, 99 languages, ~0.46s latency/10s audio on T4.
"""
from __future__ import annotations

import logging

from autovid.schemas.transcript import WordSegment

logger = logging.getLogger(__name__)


class WhisperLocalAdapter:
    """Local Whisper ASR via faster-whisper."""

    def __init__(
        self,
        model: str = "openai/whisper-large-v3-turbo",
        device: str = "cuda:0",
        compute_type: str = "float16",
    ) -> None:
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self) -> None:
        """Lazy-load the Whisper model."""
        if self._model is not None:
            return
        # TODO: from faster_whisper import WhisperModel
        # self._model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
        logger.info("Loaded Whisper model: %s on %s", self.model_name, self.device)

    def transcribe(
        self, audio_uri: str, language: str = "auto"
    ) -> list[WordSegment]:
        """Transcribe audio to word-level segments."""
        self._load_model()
        # TODO: Download audio from object store to temp file
        # TODO: segments, info = self._model.transcribe(audio_path, word_timestamps=True)
        # TODO: Convert to WordSegment list
        logger.info("Transcribing: %s (lang=%s)", audio_uri, language)
        return []

    def supported_languages(self) -> list[str]:
        return ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh", "auto"]
