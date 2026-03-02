"""Graph event taxonomy constants."""
from __future__ import annotations

GRAPH_GATE_EVENT = "graph.gate"
GRAPH_STATE_EVENT = "graph.state"

# Node lifecycle uses existing AgentTracer events for UI compatibility.
NODE_START_EVENT = "agent.start"
NODE_END_EVENT = "agent.end"

# Additional lifecycle emitted by existing pipeline.
PIPELINE_START_EVENT = "pipeline.start"
PIPELINE_END_EVENT = "pipeline.end"

