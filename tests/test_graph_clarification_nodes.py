from __future__ import annotations

import asyncio

from server.graph.artifacts import IntentBrief, PlanningInput, ResearchPack, VideoSummary
from server.graph.base import CLARIFICATION_AGENT, NodeRuntime
from server.graph.nodes.clarification import ClarificationAgent
from server.graph.state import ArtifactPatch, StatePatch, apply_state_patch, new_graph_state
from server.graph.tools import ToolDefinition, ToolRegistry


def _base_state():
    state = new_graph_state("proj_nodes")
    return apply_state_patch(
        state,
        patch=StatePatch(
            artifact_patch=ArtifactPatch(
                planning_input=PlanningInput(
                    request_id="req_nodes",
                    summaries=[
                        VideoSummary(
                            filename="clip.mp4",
                            duration_s=12,
                            summary="Person walks into frame and starts explaining a recipe.",
                        )
                    ],
                ),
                intent_brief=IntentBrief(
                    summary="Create a concise recipe highlight edit.",
                    goals=["keep strongest cooking moments"],
                    constraints=["final cut should be short"],
                    open_questions=["target duration"],
                ),
                research_pack=ResearchPack(findings=[], unresolved=["target duration", "style"]),
            ),
        ),
    )


def _runtime_with_response(response: str) -> NodeRuntime:
    async def fake_llm(payload):  # type: ignore[no-untyped-def]
        return {"content": response}

    registry = ToolRegistry(allowlists={CLARIFICATION_AGENT: {"llm_chat"}})
    registry.register(ToolDefinition(name="llm_chat", description="fake", handler=fake_llm))
    return NodeRuntime(config={}, tools=registry, tracer=None)


def _question_ids(question_set) -> set[str]:  # type: ignore[no-untyped-def]
    return {q.id for q in question_set.questions}


def test_clarification_node_happy_path() -> None:
    agent = ClarificationAgent()
    state = _base_state()
    runtime = _runtime_with_response(
        """
        {
          "analysis": "The clip shows clear instructional content.",
          "suggested_storylines": [
            {"title":"Recipe Sprint","description":"Fast cuts through prep and reveal."}
          ],
          "questions": [
            {
              "id":"focus",
              "text":"Prioritize instruction or entertainment?",
              "options":["Instruction","Entertainment"]
            }
          ]
        }
        """
    )

    patch = asyncio.run(agent.run(state, runtime))
    assert patch.artifact_patch is not None
    question_set = patch.artifact_patch.question_set
    assert question_set is not None
    assert question_set.analysis.startswith("The clip shows")
    assert "video_length" in _question_ids(question_set)
    assert "video_style" in _question_ids(question_set)


def test_clarification_node_malformed_output_fallback() -> None:
    agent = ClarificationAgent()
    state = _base_state()
    runtime = _runtime_with_response("this is not json")

    patch = asyncio.run(agent.run(state, runtime))
    assert patch.artifact_patch is not None
    question_set = patch.artifact_patch.question_set
    assert question_set is not None
    ids = _question_ids(question_set)
    assert "video_length" in ids
    assert "video_style" in ids
    assert "include_exclude" in ids
