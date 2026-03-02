"""LangGraph scaffold and phase-2 clarification flows."""
from __future__ import annotations

import logging
from typing import Any

from typing_extensions import TypedDict

from server.config import get_settings
from server.graph.artifacts import (
    AnswerSet,
    PlanningInput,
    StructuredPromptArtifact,
    UserApproval,
    VideoSummary,
)
from server.graph.base import (
    AGENT_NAMES,
    CLARIFICATION_AGENT,
    EDITING_SYNTHESIS_AGENT,
    FINAL_QA_AGENT,
    GATE_QA_PASSED,
    INTERNAL_VERIFICATION_AGENT,
    PLANNING_AGENT,
    REMOTION_SYNTHESIS_AGENT,
    RESEARCH_AGENT,
    SYNTHESIS_AGENT,
    USER_VERIFICATION_AGENT,
    GraphNode,
    NodeRuntime,
)
from server.graph.nodes import (
    ClarificationAgent,
    EditingSynthesisAgent,
    FinalQAAgent,
    InternalVerificationAgent,
    PlanningAgent,
    RemotionSynthesisAgent,
    ResearchAgent,
    SynthesisAgent,
    UserVerificationAgent,
)
from server.graph.runtime import (
    build_runtime as _runtime_build_runtime,
)
from server.graph.runtime import (
    extract_video_summaries as _runtime_extract_video_summaries,
)
from server.graph.runtime import (
    initial_artifact_patch as _runtime_initial_artifact_patch,
)
from server.graph.state import (
    GraphState,
    StatePatch,
    apply_state_patch,
    new_graph_state,
)
from server.graph.tracing import GraphTraceAdapter
from server.schemas.composition import Composition

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ModuleNotFoundError:
    END = "__end__"
    START = "__start__"
    StateGraph = None
    LANGGRAPH_AVAILABLE = False

logger = logging.getLogger(__name__)


class GraphEnvelope(TypedDict):
    """LangGraph state envelope."""

    state: GraphState


def build_foundation_graph() -> Any:
    """Build a pass-through graph for scaffold validation.

    This intentionally has no business logic. Each node returns state unchanged.
    """
    if not LANGGRAPH_AVAILABLE or StateGraph is None:
        raise RuntimeError("langgraph is not installed. Install dependencies and try again.")

    builder = StateGraph(GraphEnvelope)
    for node_name in AGENT_NAMES:
        builder.add_node(node_name, _identity_node)

    builder.add_edge(START, AGENT_NAMES[0])
    for current, nxt in _pairwise(AGENT_NAMES):
        builder.add_edge(current, nxt)
    builder.add_edge(AGENT_NAMES[-1], END)
    return builder.compile()


async def run_clarification_questions_graph(
    project: dict[str, Any],
    *,
    request_id: str = "",
) -> dict[str, Any]:
    """Run planning -> research -> clarification and return question payload."""
    if not LANGGRAPH_AVAILABLE or StateGraph is None:
        raise RuntimeError("langgraph is not installed")

    project_id = str(project.get("id", ""))
    logger.info("graph.questions.start project_id=%s", project_id)
    trace = GraphTraceAdapter(project_id=project_id)
    runtime = _build_runtime(project, trace=trace)
    graph = _build_questions_graph(runtime, trace)

    state = new_graph_state(project_id=project_id)
    state = apply_state_patch(
        state,
        patch=_initial_artifact_patch(
            planning_input=PlanningInput(
                summaries=_extract_video_summaries(project),
                request_id=request_id,
            ),
        ),
    )
    result = await graph.ainvoke({"state": state})
    final_state = result["state"]
    question_set = final_state.artifacts.question_set
    if question_set is None:
        raise RuntimeError("Question set missing from graph output")

    payload = {
        "analysis": question_set.analysis,
        "intro": question_set.intro,
        "suggested_storylines": [
            s.model_dump(exclude={"schema_version"})
            for s in question_set.suggested_storylines
        ],
        "questions": [q.model_dump(exclude={"schema_version"}) for q in question_set.questions],
    }
    logger.info(
        "graph.questions.complete project_id=%s questions=%d",
        project_id,
        len(payload["questions"]),
    )
    return payload


async def run_user_verification_graph(
    project: dict[str, Any],
    *,
    answers: dict[str, str],
    request_id: str = "",
) -> dict[str, Any]:
    """Run planning -> research -> user_verification and return structured prompt."""
    if not LANGGRAPH_AVAILABLE or StateGraph is None:
        raise RuntimeError("langgraph is not installed")

    project_id = str(project.get("id", ""))
    logger.info("graph.verify.start project_id=%s", project_id)
    trace = GraphTraceAdapter(project_id=project_id)
    runtime = _build_runtime(project, trace=trace)
    graph = _build_user_verification_graph(runtime, trace)

    state = new_graph_state(project_id=project_id)
    state = apply_state_patch(
        state,
        patch=_initial_artifact_patch(
            planning_input=PlanningInput(
                summaries=_extract_video_summaries(project),
                request_id=request_id,
            ),
            answer_set=AnswerSet(answers=answers),
        ),
    )
    result = await graph.ainvoke({"state": state})
    final_state = result["state"]
    structured_prompt = final_state.artifacts.structured_prompt
    if structured_prompt is None or not structured_prompt.structured_prompt:
        raise RuntimeError("Structured prompt missing from graph output")

    payload = {
        "status": structured_prompt.status,
        "structured_prompt": structured_prompt.structured_prompt,
    }
    logger.info(
        "graph.verify.complete project_id=%s prompt_chars=%d",
        project_id,
        len(payload["structured_prompt"]),
    )
    return payload


async def run_editing_pipeline_graph(project: dict[str, Any]) -> dict[str, Any]:
    """Run synthesis+verification graph and render after QA gate passes."""
    if not LANGGRAPH_AVAILABLE or StateGraph is None:
        raise RuntimeError("langgraph is not installed")

    project_id = str(project.get("id", ""))
    logger.info("graph.edit.start project_id=%s", project_id)
    trace = GraphTraceAdapter(project_id=project_id)
    runtime = _build_runtime(project, trace=trace)
    graph = _build_editing_graph(runtime, trace)

    state = new_graph_state(project_id=project_id)
    state = apply_state_patch(
        state,
        patch=_initial_artifact_patch(
            planning_input=PlanningInput(
                summaries=_extract_video_summaries(project),
                request_id=f"req_{project_id}",
            ),
        ),
    )
    state = state.model_copy(
        update={
            "status": "running",
            "artifacts": state.artifacts.model_copy(
                update={
                    "user_approval": UserApproval(
                        status="approved",
                        feedback="Approved via /edit endpoint",
                    ),
                    "structured_prompt": StructuredPromptArtifact(
                        status="ready",
                        structured_prompt=str(project.get("structured_prompt", "")),
                    ),
                }
            ),
        }
    )

    recursion_limit = max(8, int(get_settings().graph_max_steps))
    result = await graph.ainvoke({"state": state}, config={"recursion_limit": recursion_limit})
    final_state = result["state"]

    draft = final_state.artifacts.composition_draft
    if draft is None or not draft.composition:
        raise RuntimeError("Graph editing produced no composition payload.")

    composition = Composition.model_validate(draft.composition)

    from server.sandbox.client import render_composition

    output_uri = await render_composition(composition, project_id=project_id)
    logger.info("graph.edit.complete project_id=%s output_uri=%s", project_id, output_uri)
    return {"output_uri": output_uri, "state": final_state}


def create_initial_envelope(project_id: str, *, run_id: str | None = None) -> GraphEnvelope:
    """Create a graph envelope with a fresh GraphState."""
    return {"state": new_graph_state(project_id=project_id, run_id=run_id)}


def _identity_node(envelope: GraphEnvelope) -> GraphEnvelope:
    return {"state": envelope["state"]}


def _pairwise(items: tuple[str, ...]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for idx in range(len(items) - 1):
        pairs.append((items[idx], items[idx + 1]))
    return pairs


def _build_questions_graph(runtime: NodeRuntime, trace: GraphTraceAdapter) -> Any:
    builder = StateGraph(GraphEnvelope)
    nodes: list[GraphNode] = [
        PlanningAgent(),
        ResearchAgent(),
        ClarificationAgent(),
    ]
    _add_nodes(builder, nodes, runtime, trace)
    _chain(builder, [PLANNING_AGENT, RESEARCH_AGENT, CLARIFICATION_AGENT])
    return builder.compile()


def _build_user_verification_graph(runtime: NodeRuntime, trace: GraphTraceAdapter) -> Any:
    builder = StateGraph(GraphEnvelope)
    nodes: list[GraphNode] = [
        PlanningAgent(),
        ResearchAgent(),
        UserVerificationAgent(),
    ]
    _add_nodes(builder, nodes, runtime, trace)
    _chain(builder, [PLANNING_AGENT, RESEARCH_AGENT, USER_VERIFICATION_AGENT])
    return builder.compile()


def _build_editing_graph(runtime: NodeRuntime, trace: GraphTraceAdapter) -> Any:
    builder = StateGraph(GraphEnvelope)
    nodes: list[GraphNode] = [
        SynthesisAgent(),
        RemotionSynthesisAgent(),
        EditingSynthesisAgent(),
    ]
    _add_nodes(builder, nodes, runtime, trace)

    builder.add_edge(START, SYNTHESIS_AGENT)
    builder.add_edge(SYNTHESIS_AGENT, REMOTION_SYNTHESIS_AGENT)
    builder.add_edge(REMOTION_SYNTHESIS_AGENT, EDITING_SYNTHESIS_AGENT)
    builder.add_edge(EDITING_SYNTHESIS_AGENT, END)
    return builder.compile()


def _add_nodes(
    builder: Any,
    nodes: list[GraphNode],
    runtime: NodeRuntime,
    trace: GraphTraceAdapter,
) -> None:
    for node in nodes:
        builder.add_node(node.name, _wrap_node(node, runtime, trace))


def _chain(builder: Any, names: list[str]) -> None:
    if not names:
        return
    builder.add_edge(START, names[0])
    for idx in range(len(names) - 1):
        builder.add_edge(names[idx], names[idx + 1])
    builder.add_edge(names[-1], END)


def _wrap_node(node: GraphNode, runtime: NodeRuntime, trace: GraphTraceAdapter) -> Any:
    async def _runner(envelope: GraphEnvelope) -> GraphEnvelope:
        state = envelope["state"]
        before = dict(state.gates)
        logger.info("graph.node.start project_id=%s node=%s", state.project_id, node.name)
        trace.node_start(node.name)

        node_tracer = trace.get_tracer(node.name)
        runtime._node_tracer = node_tracer

        try:
            patch = await node.run(state, runtime)
            next_state = apply_state_patch(state, patch)
            summary = ", ".join(d.decision for d in patch.decisions) if patch.decisions else ""

            trace.node_end(node.name, summary=summary[:500])
            logger.info(
                "graph.node.complete project_id=%s node=%s summary=%s",
                state.project_id,
                node.name,
                summary[:120],
            )
        except Exception as exc:
            trace.node_end(node.name, error=str(exc))
            logger.exception(
                "graph.node.error project_id=%s node=%s error=%s",
                state.project_id,
                node.name,
                exc,
            )
            raise
        finally:
            runtime._node_tracer = None

        _emit_gate_decisions(before, next_state.gates, trace)
        trace.state_snapshot(next_state, node_name=node.name)
        return {"state": next_state}

    return _runner


def _emit_gate_decisions(
    before: dict[str, bool],
    after: dict[str, bool],
    trace: GraphTraceAdapter,
) -> None:
    for gate, new_value in after.items():
        old_value = before.get(gate, False)
        if new_value != old_value:
            logger.info("graph.gate gate=%s opened=%s", gate, new_value)
            trace.gate_decision(gate, new_value, reason="state_transition")


_MAX_VERIFICATION_RETRIES = 2


def _route_after_internal_verification(envelope: GraphEnvelope) -> str:
    state = envelope["state"]
    if state.gates.get("internal_verified", False):
        return FINAL_QA_AGENT

    retry_count = sum(
        1 for d in state.decisions
        if d.node == INTERNAL_VERIFICATION_AGENT and d.decision == "internal_verification_failed"
    )
    if retry_count >= _MAX_VERIFICATION_RETRIES:
        logger.warning(
            "Internal verification failed %d times, forcing pass to Final QA",
            retry_count,
        )
        return FINAL_QA_AGENT

    if state.next_node in {SYNTHESIS_AGENT, REMOTION_SYNTHESIS_AGENT, EDITING_SYNTHESIS_AGENT}:
        return str(state.next_node)
    return EDITING_SYNTHESIS_AGENT


_MAX_QA_RETRIES = 1


def _route_after_final_qa(envelope: GraphEnvelope) -> str:
    state = envelope["state"]
    if state.gates.get(GATE_QA_PASSED, False):
        return "__end__"

    qa_fail_count = sum(
        1 for d in state.decisions
        if d.node == FINAL_QA_AGENT and d.decision == "qa_failed"
    )
    if qa_fail_count >= _MAX_QA_RETRIES:
        logger.warning(
            "Final QA failed %d times, forcing completion",
            qa_fail_count,
        )
        return "__end__"

    return EDITING_SYNTHESIS_AGENT


def _build_runtime(project: dict[str, Any], *, trace: GraphTraceAdapter) -> NodeRuntime:
    return _runtime_build_runtime(project, trace=trace)


def _extract_video_summaries(project: dict[str, Any]) -> list[VideoSummary]:
    return _runtime_extract_video_summaries(project)


def _initial_artifact_patch(
    *,
    planning_input: PlanningInput,
    answer_set: AnswerSet | None = None,
) -> StatePatch:
    return _runtime_initial_artifact_patch(
        planning_input=planning_input,
        answer_set=answer_set,
    )
