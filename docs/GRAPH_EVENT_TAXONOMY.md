# Graph Event Taxonomy

This document defines the event names emitted by the graph orchestration layer and the expected payload shape.

## Lifecycle Events

- `pipeline.start`
  - Emitted by route layer before graph edit execution begins.
  - Fields: `nodeId=pipeline`.
- `pipeline.end`
  - Emitted by route layer after graph or legacy edit flow completes/fails.
  - Fields: `nodeId=pipeline`, `status`, optional `error`.

## Node Events

Graph nodes use existing `AgentTracer` events for compatibility with the trace UI.

- `agent.start`
  - Emitted when each graph node starts.
  - Fields: `nodeId=agent:<node_name>`, `name`, optional `maxTurns`.
- `agent.end`
  - Emitted when each graph node completes or fails.
  - Fields: `nodeId=agent:<node_name>`, `status`, `summary`, optional `error`.

## Graph-Specific Events

- `graph.gate`
  - Emitted when any gate changes value.
  - Fields: `nodeId=gate:<gate_name>`, `gate`, `opened`, `reason`.
- `graph.state`
  - Emitted after node completion with compact state snapshot.
  - Fields: `nodeId=graph:<node_name>`, `status`, `openGates`.

## Gate Names

- `plan_done`
- `research_done`
- `user_verified`
- `internal_verified`
- `synthesis_done`
- `qa_passed`

## Node Names

- `planning`
- `research`
- `clarification`
- `user_verification`
- `synthesis`
- `remotion_synthesis`
- `editing_synthesis`
- `internal_verification`
- `final_qa`
