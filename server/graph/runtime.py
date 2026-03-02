"""Runtime and tool-registry helpers for graph execution."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from server.config import load_graph_config
from server.graph.artifacts import AnswerSet, PlanningInput, VideoSummary
from server.graph.base import (
    CLARIFICATION_AGENT,
    EDITING_SYNTHESIS_AGENT,
    FINAL_QA_AGENT,
    INTERNAL_VERIFICATION_AGENT,
    PLANNING_AGENT,
    REMOTION_SYNTHESIS_AGENT,
    RESEARCH_AGENT,
    SYNTHESIS_AGENT,
    NodeRuntime,
)
from server.graph.state import ArtifactPatch, StatePatch
from server.graph.tools import ToolDefinition, ToolRegistry, default_tool_registry

if TYPE_CHECKING:
    from collections.abc import Mapping

    from server.graph.tracing import GraphTraceAdapter


def build_runtime(project: dict[str, Any], *, trace: GraphTraceAdapter) -> NodeRuntime:
    """Build runtime dependencies passed to each graph node."""
    cfg = load_graph_config()
    agents = cfg.get("agents", {})
    runtime_cfg = {"agents": agents if isinstance(agents, dict) else {}, "project": project}
    runtime = NodeRuntime(config=runtime_cfg, tools=None, tracer=trace)
    tools = build_tool_registry(runtime)
    runtime.tools = tools
    return runtime


def extract_video_summaries(project: dict[str, Any]) -> list[VideoSummary]:
    """Extract typed summary inputs from project ingestion data."""
    from server.agents.clarifying import extract_video_summaries as _extract

    raw = _extract(project)
    return [
        VideoSummary(
            filename=str(item.get("filename", "")),
            duration_s=float(item.get("duration_s", 0.0)),
            summary=str(item.get("summary", "")),
        )
        for item in raw
    ]


def initial_artifact_patch(
    *,
    planning_input: PlanningInput,
    answer_set: AnswerSet | None = None,
) -> StatePatch:
    """Create initial state patch for graph runs."""
    return StatePatch(
        artifact_patch=ArtifactPatch(
            planning_input=planning_input,
            answer_set=answer_set,
        )
    )


def build_tool_registry(runtime: NodeRuntime) -> ToolRegistry:
    """Build tool registry with allowlists for graph agents."""
    from server.agents import clarifying as clarifying_agent
    from server.agents import tools as editing_tools
    from server.config import get_settings

    async def _llm_chat(payload: Mapping[str, Any]) -> dict[str, Any]:
        messages = payload.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")

        s = get_settings()
        model = s.clarifying_model
        temperature = float(payload.get("temperature", 0.2))
        max_tokens = int(payload.get("max_tokens", 2048))

        tracer = getattr(runtime, "_node_tracer", None)
        if tracer:
            tracer.on_llm_start(messages=messages, model=model)

        content, usage = await clarifying_agent._call_llm(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            project_id=str(payload.get("project_id", "")) or None,
            request_id=str(payload.get("request_id", "")) or None,
        )

        if tracer:
            tracer.on_llm_end(
                content=content[:1000] if content else None,
                tool_calls=None,
                usage=usage if isinstance(usage, dict) else None,
            )

        return {"content": content, "usage": usage}

    def _plan_clips(payload: Mapping[str, Any]) -> dict[str, Any]:
        project = payload.get("project", {})
        previous_failure = bool(payload.get("previous_failure", False))
        if not isinstance(project, dict):
            raise ValueError("project payload must be an object")
        clips = editing_tools.plan_clip_specs(project, previous_failure=previous_failure)
        return {"clips": clips}

    def _compose_from_clips(payload: Mapping[str, Any]) -> dict[str, Any]:
        clips = payload.get("clips", [])
        key_to_path = payload.get("key_to_path", {})
        if not isinstance(clips, list) or not isinstance(key_to_path, dict):
            raise ValueError("compose_from_clips requires clips(list) and key_to_path(dict)")
        composition = editing_tools.build_composition_from_clip_specs(clips, key_to_path)
        return {"composition": composition.model_dump()}

    def _edit_spec_to_timeline(payload: Mapping[str, Any]) -> dict[str, Any]:
        edit_spec = payload.get("edit_spec", {})
        if not isinstance(edit_spec, dict):
            raise ValueError("edit_spec_to_timeline requires edit_spec(dict)")
        layers = []
        for idx, clip in enumerate(edit_spec.get("clips", [])):
            if not isinstance(clip, dict):
                continue
            layers.append(
                {
                    "type": "video",
                    "z_index": idx,
                    "source": clip.get("source_video", ""),
                    "start_s": float(clip.get("start_s", 0.0)),
                    "end_s": float(clip.get("end_s", 0.0)),
                }
            )
        return {"timeline": {"layers": layers}, "warnings": []}

    registry = default_tool_registry()
    registry.register(
        ToolDefinition(
            name="llm_chat",
            description="Chat completion returning assistant content",
            handler=_llm_chat,
        )
    )
    registry.register(
        ToolDefinition(
            name="plan_clips",
            description="Build deterministic clip plan from project context",
            handler=_plan_clips,
        )
    )
    registry.register(
        ToolDefinition(
            name="compose_from_clips",
            description="Build composition payload from clip specs",
            handler=_compose_from_clips,
        )
    )
    registry.register(
        ToolDefinition(
            name="edit_spec_to_timeline",
            description="Convert edit spec to timeline layers",
            handler=_edit_spec_to_timeline,
        )
    )

    llm_agents = {
        PLANNING_AGENT, RESEARCH_AGENT, CLARIFICATION_AGENT,
        SYNTHESIS_AGENT, INTERNAL_VERIFICATION_AGENT, FINAL_QA_AGENT,
    }
    for agent_name in llm_agents:
        registry.set_allowlist(agent_name, {"llm_chat"})
    registry.set_allowlist(REMOTION_SYNTHESIS_AGENT, {"edit_spec_to_timeline"})
    return registry
