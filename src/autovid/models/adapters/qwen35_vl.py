"""Qwen3.5-397B-A17B VLM Adapter (Primary).

Native vision-language model with early-fusion video token training.
MoE architecture: 17B active params out of 397B total.
Served via vLLM or NVIDIA NIM. Processes raw video chunks natively.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from autovid.schemas.vlm import (
    BoundingBox,
    ChunkVLMAnalysis,
    FrameAnalysis,
)

logger = logging.getLogger(__name__)


class Qwen35VLAdapter:
    """Primary VLM adapter: Qwen3.5-397B-A17B via vLLM/NIM."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen3.5-397B-A17B-Instruct",
        native_video_input: bool = True,
        max_chunk_duration_s: int = 30,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.native_video_input = native_video_input
        self.max_chunk_duration_s = max_chunk_duration_s

    def describe_frame(self, image_uri: str, prompt: str) -> FrameAnalysis:
        """Single-frame analysis for on-demand follow-up queries."""
        # TODO: Call vLLM/NIM API with image + prompt
        logger.info("Describe frame: %s", image_uri)
        return FrameAnalysis(caption="", tags=[])

    def describe_frames_batch(
        self, image_uris: list[str], prompt: str
    ) -> list[FrameAnalysis]:
        """Batch frame analysis."""
        return [self.describe_frame(uri, prompt) for uri in image_uris]

    def analyze_video_chunk(
        self, video_uri: str, prompt: str, fps: int = 1
    ) -> ChunkVLMAnalysis:
        """Dense per-second analysis with native video input.

        Sends the raw video chunk to Qwen3.5 as video tokens (early-fusion).
        The model processes the entire chunk temporally and returns structured
        JSON with per-second SecondAnalysis entries.
        """
        logger.info(
            "Analyzing chunk: %s at %d FPS (native=%s)",
            video_uri, fps, self.native_video_input,
        )

        # TODO: Build API request with video URI and system prompt
        # TODO: Call vLLM/NIM chat completions API
        # TODO: Parse structured JSON response
        # TODO: Validate and return ChunkVLMAnalysis

        raise NotImplementedError("Qwen3.5 VLM inference not yet implemented")

    def locate_subject(self, image_uri: str, query: str) -> BoundingBox:
        """Spatial grounding: locate a subject in a frame."""
        # TODO: Call VLM with grounding prompt
        logger.info("Locate subject: '%s' in %s", query, image_uri)
        return BoundingBox(x=0.4, y=0.2, width=0.2, height=0.3)
