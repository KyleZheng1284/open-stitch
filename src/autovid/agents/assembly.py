"""Assembly Agent — validates composition and triggers sandbox render.

The Assembly Agent is thin by design. All creative decisions (what segments,
what overlays, what transitions) are made upstream by the ReAct loop and
post-processing agents. Assembly validates, resolves URIs, serializes to
TimelineJSON, and executes the rendering pipeline inside the sandbox.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas.composition import RemotionComposition
from autovid.schemas.timeline import TimelineJSON

logger = logging.getLogger(__name__)


class AssemblyAgent:
    """Validates composition and triggers sandbox rendering."""

    async def run(
        self,
        composition: RemotionComposition,
        sandbox_id: str,
    ) -> list[str]:
        """Validate composition, render in sandbox, export results.

        Returns list of rendered clip URIs in object store.
        """
        logger.info(
            "Assembly agent: %d layers, %d ms total duration",
            composition.layer_count,
            composition.total_duration_ms,
        )

        # Step 1: Validate composition
        self._validate(composition)

        # Step 2: Resolve asset URIs to sandbox paths
        self._resolve_uris(composition, sandbox_id)

        # Step 3: Serialize to TimelineJSON
        timeline = TimelineJSON.from_composition(composition)
        timeline_json = timeline.model_dump_json(indent=2)
        logger.info("Serialized timeline: %d bytes", len(timeline_json))

        # Step 4: Write timeline to sandbox
        # TODO: sandbox_write_file(f"/workspace/intermediate/timeline/{composition.clip_id}.json", timeline_json)

        # Step 5: Render with Remotion inside sandbox
        # TODO: sandbox_render_remotion(timeline_dict, f"/workspace/output/{composition.clip_id}_video.mp4")

        # Step 6: Mix audio with FFmpeg
        # TODO: sandbox_run_ffmpeg([...audio mixing args...])

        # Step 7: Export final clip to object store
        # TODO: uri = sandbox_export_to_store(f"/workspace/output/{composition.clip_id}.mp4")

        return []  # TODO: return list of exported URIs

    def _validate(self, composition: RemotionComposition) -> None:
        """Validate composition integrity before rendering."""
        if not composition.sequences:
            raise ValueError("Composition has no video sequences")

        # Check z-index conflicts
        z_indices: dict[int, int] = {}
        for layer in composition.all_layers_sorted():
            z = getattr(layer, "z_index", 0)
            z_indices[z] = z_indices.get(z, 0) + 1

        # Check sequence continuity
        sorted_seqs = sorted(
            composition.sequences, key=lambda s: s.position_in_timeline_ms
        )
        for i in range(len(sorted_seqs) - 1):
            gap = (
                sorted_seqs[i + 1].position_in_timeline_ms
                - sorted_seqs[i].position_in_timeline_ms
                - sorted_seqs[i].output_duration_ms
            )
            if gap > 1000:  # > 1s gap
                logger.warning(
                    "Gap of %d ms between sequences %s and %s",
                    gap, sorted_seqs[i].id, sorted_seqs[i + 1].id,
                )

        logger.info("Composition validated: %s", {f"z={k}": v for k, v in sorted(z_indices.items())})

    def _resolve_uris(self, composition: RemotionComposition, sandbox_id: str) -> None:
        """Resolve relative asset URIs to absolute sandbox paths."""
        # TODO: Map sandbox-relative paths to /workspace/... absolute paths
        # TODO: Verify all referenced assets exist in the sandbox
        pass
