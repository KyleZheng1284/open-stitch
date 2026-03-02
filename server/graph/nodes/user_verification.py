"""User verification node for phase-2 clarification graph."""
from __future__ import annotations

from server.config import load_prompt
from server.graph.artifacts import StructuredPromptArtifact, UserApproval
from server.graph.base import GATE_USER_VERIFIED, USER_VERIFICATION_AGENT, NodeRuntime
from server.graph.state import ArtifactPatch, DecisionRecord, GraphState, StatePatch


class UserVerificationAgent:
    """Converts user answers into approved structured editing intent."""

    name = USER_VERIFICATION_AGENT
    prompt_file = "graph_user_verification.txt"

    async def run(self, state: GraphState, runtime: NodeRuntime) -> StatePatch:
        answer_set = state.artifacts.answer_set
        if answer_set is None:
            raise RuntimeError("answer_set artifact is required")

        from server.agents.clarifying import build_structured_prompt

        # Prompt file is loaded to keep this node prompt-driven and configurable.
        prompt_header = load_prompt(self.prompt_file).strip()
        structured_prompt = build_structured_prompt(
            project=runtime.config.get("project", {}),
            answers=answer_set.answers,
        )
        final_prompt = (
            f"{prompt_header}\n\n{structured_prompt}"
            if prompt_header
            else structured_prompt
        )

        return StatePatch(
            current_node=self.name,
            gates={GATE_USER_VERIFIED: True},
            artifact_patch=ArtifactPatch(
                user_approval=UserApproval(
                    status="approved",
                    feedback="Answers captured and verified for editing handoff.",
                    revision_notes=[],
                ),
                structured_prompt=StructuredPromptArtifact(
                    status="ready",
                    structured_prompt=final_prompt,
                ),
            ),
            decisions=[DecisionRecord(node=self.name, decision="user_verified")],
        )
