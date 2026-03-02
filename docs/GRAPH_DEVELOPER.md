# Graph Developer Guide

## Add a New Node

1. Create a node file in `server/graph/nodes/`.
2. Implement class shape:
   - `name: str` (use constants from `server/graph/base.py`)
   - `async def run(self, state, runtime) -> StatePatch`
3. Read from typed artifacts only (`state.artifacts`).
4. Write outputs using `ArtifactPatch` in a returned `StatePatch`.
5. Add deterministic `DecisionRecord` entries for traceability.
6. Register the node in `server/graph/nodes/__init__.py`.
7. Wire routing in `server/graph/graph.py` (linear or conditional edges).
8. Add unit tests for happy path and failure path.

## Add a New Tool

1. Implement tool function in `server/agents/tools.py` (pure function if possible).
2. Register it in `server/graph/runtime.py` via `ToolDefinition`.
3. Add agent allowlist entry with `registry.set_allowlist(...)`.
4. Add tests for:
   - expected output
   - invalid payload handling
   - allowlist enforcement

## Validation and Loopback

- Put deterministic validators in `server/graph/validators.py`.
- Internal verification should emit actionable codes and set `next_node`.
- Keep retry targets narrow (`synthesis`, `remotion_synthesis`, `editing_synthesis`).

## Logging and Events

- Node lifecycle is emitted through `GraphTraceAdapter` and `AgentTracer`.
- Gate/state events must use taxonomy constants in `server/graph/events.py`.
- Keep `DecisionRecord.detail` short and machine-parseable where possible.

## Safety Rules

- Do not remove legacy route fallback.
- Keep feature flags functional:
  - `GRAPH_ENABLED`
  - `GRAPH_FAIL_OPEN`
- Rendering must only happen when `qa_passed` is true.
