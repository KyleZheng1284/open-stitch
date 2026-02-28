"""Director Agent — top-level orchestrator.

Receives a ProjectRequest, spawns the Docker sandbox, kicks off the ReAct
reasoning loop, dispatches parallel post-processing agents (Subtitle, Music,
Meme/SFX), collects results, and triggers final rendering via Assembly.

Implemented as a LangGraph StateGraph with branching and parallel fan-out.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from autovid.schemas import ProjectRequest, ProjectResult
from autovid.schemas.composition import RemotionComposition

from .assembly import AssemblyAgent
from .composition_state import CompositionStateManager
from .meme_sfx import MemeSFXAgent
from .music import MusicAgent
from .react_loop import ReActReasoningLoop
from .subtitle import SubtitleAgent

logger = logging.getLogger(__name__)


class DirectorAgent:
    """Top-level pipeline orchestrator.

    Flow:
    1. Read chunk metadata from ChunkStore
    2. Spawn sandbox container
    3. Run ReAct loop -> produces initial RemotionComposition
    4. Fan-out: Subtitle + Music + Meme/SFX agents (parallel)
    5. Fan-in: Assembly Agent validates + renders in sandbox
    6. Publishing Agent uploads to social platforms
    """

    def __init__(self) -> None:
        self.react_loop = ReActReasoningLoop()
        self.subtitle_agent = SubtitleAgent()
        self.music_agent = MusicAgent()
        self.meme_sfx_agent = MemeSFXAgent()
        self.assembly_agent = AssemblyAgent()
        self.composition_mgr = CompositionStateManager()

    async def run(self, request: ProjectRequest) -> ProjectResult:
        """Execute the full editing pipeline for a project."""
        logger.info("Director starting for project %s", request.project_id)

        # TODO: Read chunk metadata from ChunkStore
        chunk_metadata: list[Any] = []

        # TODO: Spawn sandbox container via SandboxManager
        sandbox_id: str = ""

        # Step 1: ReAct reasoning loop -> initial composition
        composition = RemotionComposition()
        logger.info("Running ReAct reasoning loop")
        composition = await self.react_loop.run(
            project=request,
            chunks=chunk_metadata,
            composition=composition,
        )

        # Step 2: Parallel post-processing (independent z-index ranges)
        logger.info("Running parallel post-processing agents")
        await asyncio.gather(
            self.subtitle_agent.run(composition, chunk_metadata, request),
            self.music_agent.run(composition, chunk_metadata, request),
            self.meme_sfx_agent.run(composition, chunk_metadata, request),
        )

        # Step 3: Assembly -> validate + render in sandbox
        logger.info("Running assembly agent")
        clip_uris = await self.assembly_agent.run(
            composition=composition,
            sandbox_id=sandbox_id,
        )

        # TODO: Step 4: Publishing Agent
        logger.info("Director complete for project %s", request.project_id)

        return ProjectResult(
            project_id=request.project_id,
            job_id="",  # TODO: from job tracking
            clip_uris=clip_uris,
        )
