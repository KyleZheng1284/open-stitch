"""Whisper ASR — word-level transcription."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_whisper(audio_path: Path, model_size: str = "small", device: str = "cpu", compute: str = "int8") -> dict:
    """Run faster-whisper and return words + sentences."""
    from faster_whisper import WhisperModel

    logger.info("Loading Whisper %s on %s", model_size, device)
    model = WhisperModel(model_size, device=device, compute_type=compute)

    segments, info = model.transcribe(str(audio_path), word_timestamps=True, language="en")
    segments = list(segments)

    logger.info("ASR: lang=%s (%.2f)", info.language, info.language_probability)

    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append({
                "word": w.word.strip(),
                "start": round(w.start, 2),
                "end": round(w.end, 2),
                "confidence": round(w.probability, 2),
            })

    sentences = [
        {"text": seg.text.strip(), "start": round(seg.start, 2), "end": round(seg.end, 2)}
        for seg in segments
    ]

    return {"words": words, "sentences": sentences, "language": info.language}
