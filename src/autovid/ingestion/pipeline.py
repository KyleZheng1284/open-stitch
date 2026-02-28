"""Async ingestion pipeline orchestrator.

Triggered immediately on video upload. Coordinates the parallel execution
of ASR, Audio Analysis, and VLM workers per chunk. Results are stored in
the ChunkStore for Phase 2 agents to consume.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from autovid.schemas.chunk import AudioFeatures, ChunkMetadata
from autovid.schemas.transcript import Transcript
from autovid.schemas.vlm import ChunkVLMAnalysis

from .asr_worker import ASRWorker
from .audio_analyzer import AudioAnalyzer
from .chunker import Chunker
from .vlm_worker import VLMWorker

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates per-video async ingestion.

    For each uploaded video:
    1. Split into chunks (scene-detect + temporal)
    2. Per chunk, fan-out:
       a. ASR + Audio Analyzer run first (fast, ~2-5s)
       b. VLM runs with transcript + audio context injected
    3. Store results in ChunkStore
    """

    def __init__(self) -> None:
        self.chunker = Chunker()
        self.asr_worker = ASRWorker()
        self.audio_analyzer = AudioAnalyzer()
        self.vlm_worker = VLMWorker()

    async def on_video_uploaded(
        self, project_id: str, video_id: str, video_uri: str
    ) -> list[ChunkMetadata]:
        """Process a newly uploaded video through the full ingestion pipeline."""
        logger.info(
            "Ingestion starting: project=%s video=%s", project_id, video_id
        )

        # Step 1: Probe and normalize
        # TODO: probe_media(video_uri) -> MediaInfo
        # TODO: transcode_to_standard(video_uri) -> normalized_uri

        # Step 2: Split into chunks
        chunks = await self.chunker.split(video_uri)
        logger.info("Split into %d chunks", len(chunks))

        # Step 3: Process each chunk in parallel
        results: list[ChunkMetadata] = []
        tasks = [
            self._process_chunk(project_id, video_id, chunk, idx)
            for idx, chunk in enumerate(chunks)
        ]
        results = await asyncio.gather(*tasks)

        logger.info("Ingestion complete: %d chunks processed", len(results))
        return results

    async def _process_chunk(
        self,
        project_id: str,
        video_id: str,
        chunk: dict[str, Any],
        chunk_index: int,
    ) -> ChunkMetadata:
        """Process a single chunk: ASR + Audio -> VLM -> store."""
        chunk_id = f"{video_id}_chunk_{chunk_index:03d}"

        # Phase A: ASR + Audio run in parallel (fast)
        transcript, audio_features = await asyncio.gather(
            self.asr_worker.transcribe(chunk["audio_uri"]),
            self.audio_analyzer.analyze(chunk["audio_uri"]),
        )

        # Phase B: VLM runs with context from Phase A
        fps = 4 if audio_features.has_high_energy_second(threshold=0.7) else 1
        vlm_analysis = await self.vlm_worker.analyze_chunk(
            video_uri=chunk["video_uri"],
            fps=fps,
            transcript_context=transcript,
            audio_context=audio_features,
        )

        # Store results
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            video_id=video_id,
            project_id=project_id,
            chunk_index=chunk_index,
            start_ms=chunk["start_ms"],
            end_ms=chunk["end_ms"],
            duration_ms=chunk["end_ms"] - chunk["start_ms"],
            video_uri=chunk["video_uri"],
            audio_uri=chunk["audio_uri"],
            transcript=[],  # TODO: convert Transcript to list[WordSegment]
            vlm_analysis=vlm_analysis,
            audio_features=audio_features,
        )

        # TODO: Store in ChunkStore (database/Redis)
        return metadata
