"""Model provider protocols (contracts).

Every model-dependent step is behind a typed Protocol. Adapters implement
the protocol for specific backends (Whisper, Qwen, Llama, etc.).
Swapping models = changing config/models.yaml, no code changes.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from autovid.schemas.transcript import WordSegment
from autovid.schemas.vlm import BoundingBox, ChunkVLMAnalysis, FrameAnalysis


@runtime_checkable
class ASRProvider(Protocol):
    """Speech recognition provider contract.

    Implementations: WhisperLocalAdapter, RivaNIMAdapter, WhisperAPIAdapter
    """

    def transcribe(
        self, audio_uri: str, language: str = "auto"
    ) -> list[WordSegment]:
        """Transcribe audio to word-level segments with timestamps."""
        ...

    def supported_languages(self) -> list[str]:
        """List of supported language codes."""
        ...


@runtime_checkable
class VLMProvider(Protocol):
    """Vision-Language Model provider contract.

    The VLM is the editing pipeline's eyes. Must produce dense per-second
    understanding so agents can make precise editing decisions.

    Implementations: Qwen35VLAdapter (primary), QwenVLAdapter, LLaVAAdapter,
                     GeminiProAdapter (cloud tier), OpenAIVisionAdapter
    """

    def describe_frame(self, image_uri: str, prompt: str) -> FrameAnalysis:
        """Describe a single frame. Used for on-demand follow-up queries."""
        ...

    def describe_frames_batch(
        self, image_uris: list[str], prompt: str
    ) -> list[FrameAnalysis]:
        """Batch frame description. Fallback for non-native-video models."""
        ...

    def analyze_video_chunk(
        self, video_uri: str, prompt: str, fps: int = 1
    ) -> ChunkVLMAnalysis:
        """Dense per-second analysis of a video chunk.

        Primary ingestion method. Sends raw video to the model (native
        video tokens for Qwen3.5, frame extraction for others).
        Returns full ChunkVLMAnalysis with SecondAnalysis per second.
        """
        ...

    def locate_subject(self, image_uri: str, query: str) -> BoundingBox:
        """Spatial grounding: find a subject in a frame.

        E.g., "where is the person's face?" -> normalized BoundingBox.
        Used for precise meme placement.
        """
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Large Language Model provider contract.

    Used by the ReAct loop for reasoning, the Subtitle Agent for text
    processing, and the Meme/SFX Agent for semantic analysis.

    Implementations: LocalLlamaAdapter, NIMAdapter, OpenAIAdapter
    """

    def generate(
        self,
        messages: list[dict[str, str]],
        json_schema: dict | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text completion."""
        ...

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        """Generate structured output conforming to a Pydantic model."""
        ...
