"""ReAct Reasoning Loop — the editing brain.

Implements the Observe/Think/Act/Check cycle that reads dense per-second
VLM analysis and directly emits Remotion operations. The agent thinks in
Remotion primitives: every tool call builds the composition incrementally.

Runs 2-5 iterations (configurable) before committing a final edit plan.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas import ProjectRequest
from autovid.schemas.chunk import ChunkMetadata
from autovid.schemas.composition import RemotionComposition

logger = logging.getLogger(__name__)


class ReActReasoningLoop:
    """ReAct (Reason + Act) loop for editing decisions.

    Tools available to the agent:
    - Understanding tools: read_chunk_metadata, query_edit_signals,
      get_vlm_detail, locate_subject, find_audio_peaks, search_assets
    - Remotion tools: remotion_add_sequence, remotion_add_overlay,
      remotion_add_subtitle, remotion_add_transition, remotion_add_audio,
      remotion_set_output, remotion_preview, remotion_modify_sequence,
      remotion_remove_layer
    """

    def __init__(self, max_iterations: int = 3) -> None:
        self.max_iterations = max_iterations

    async def run(
        self,
        project: ProjectRequest,
        chunks: list[Any],
        composition: RemotionComposition,
    ) -> RemotionComposition:
        """Execute the ReAct loop, building the composition incrementally."""
        logger.info(
            "ReAct loop starting: %d chunks, max %d iterations",
            len(chunks),
            self.max_iterations,
        )

        for iteration in range(1, self.max_iterations + 1):
            logger.info("ReAct iteration %d/%d", iteration, self.max_iterations)

            # OBSERVE: Read chunk metadata and current composition state
            observations = await self._observe(chunks, composition)

            # THINK: Reason about content given style prompt
            plan = await self._think(
                observations=observations,
                style_prompt=project.style_prompt,
                preferences=project.preferences,
                iteration=iteration,
            )

            # ACT: Execute Remotion tool calls
            await self._act(plan, composition, chunks)

            # CHECK: Validate composition quality
            should_continue = await self._check(
                composition=composition,
                style_prompt=project.style_prompt,
                iteration=iteration,
            )

            if not should_continue:
                logger.info("ReAct loop converged at iteration %d", iteration)
                break

        logger.info(
            "ReAct loop complete: %d layers in composition",
            composition.layer_count,
        )
        return composition

    async def _observe(
        self, chunks: list[Any], composition: RemotionComposition
    ) -> dict[str, Any]:
        """Read chunk metadata and current composition state."""
        # TODO: Aggregate VLM analysis, transcripts, audio features
        # TODO: Identify highlight seconds, skip ranges, edit signals
        return {
            "chunk_count": len(chunks),
            "current_layers": composition.layer_count,
            "current_duration_ms": composition.total_duration_ms,
        }

    async def _think(
        self,
        observations: dict[str, Any],
        style_prompt: str,
        preferences: Any,
        iteration: int,
    ) -> dict[str, Any]:
        """Reason about editing decisions given observations and style prompt."""
        # TODO: Call LLM with observations + style prompt
        # TODO: Generate action plan (which Remotion tools to call)
        logger.info("Thinking: observations=%s", observations)
        return {"actions": []}

    async def _act(
        self,
        plan: dict[str, Any],
        composition: RemotionComposition,
        chunks: list[Any],
    ) -> None:
        """Execute planned Remotion tool calls on the composition."""
        # TODO: Call remotion_add_sequence, remotion_add_overlay, etc.
        # TODO: Each call modifies the composition in-place
        actions = plan.get("actions", [])
        logger.info("Acting: %d tool calls planned", len(actions))

    async def _check(
        self,
        composition: RemotionComposition,
        style_prompt: str,
        iteration: int,
    ) -> bool:
        """Evaluate if the composition needs further refinement.

        Returns True if more iterations are needed, False to commit.
        """
        # TODO: Call LLM to evaluate composition quality
        # TODO: Check clip count, lengths, narrative coherence, style match
        if iteration >= self.max_iterations:
            return False
        return composition.layer_count == 0
