import { create } from "zustand";
import type { TraceEvent, TraceNode, NodeKind, NodeStatus } from "../types/trace";

interface TraceState {
  nodes: Map<string, TraceNode>;
  jobStatus: "idle" | "running" | "complete" | "error";
  selectedNodeId: string | null;
  lastEventId: string | null;
  activeProjectId: string | null;
  expandedGroups: Set<string>;

  handleEvent: (event: TraceEvent) => void;
  selectNode: (id: string | null) => void;
  resetForProject: (projectId: string) => void;
  toggleGroup: (parentId: string) => void;
}

function makeNode(
  id: string,
  kind: NodeKind,
  label: string,
  status: NodeStatus,
  parentId: string | null,
  ts: number,
  data: Record<string, unknown> = {},
): TraceNode {
  return {
    id,
    kind,
    label,
    status,
    parentId,
    startedAt: ts,
    completedAt: status === "complete" ? ts : null,
    turn: 0,
    maxTurns: null,
    tokens: "",
    tokenCount: 0,
    data,
  };
}

function updateNode(
  nodes: Map<string, TraceNode>,
  id: string,
  patch: Partial<TraceNode>,
): Map<string, TraceNode> {
  const existing = nodes.get(id);
  if (!existing) return nodes;
  const next = new Map(nodes);
  next.set(id, { ...existing, ...patch });
  return next;
}

export const useTraceStore = create<TraceState>((set) => ({
  nodes: new Map(),
  jobStatus: "idle",
  selectedNodeId: null,
  lastEventId: null,
  activeProjectId: null,
  expandedGroups: new Set(),

  toggleGroup: (parentId: string) =>
    set((state) => {
      const next = new Set(state.expandedGroups);
      if (next.has(parentId)) next.delete(parentId);
      else next.add(parentId);
      return { expandedGroups: next };
    }),

  resetForProject: (projectId: string) =>
    set((state) => {
      if (state.activeProjectId === projectId) return state;
      return {
        nodes: new Map(),
        jobStatus: "idle",
        selectedNodeId: null,
        lastEventId: null,
        expandedGroups: new Set(),
        activeProjectId: projectId,
      };
    }),

  selectNode: (id) => set({ selectedNodeId: id }),

  handleEvent: (event: TraceEvent) =>
    set((state) => {
      let nodes = new Map(state.nodes);
      let jobStatus = state.jobStatus;
      const ts = event.ts;

      switch (event.type) {
        // ── Pipeline lifecycle ───────────────────────────────────
        case "pipeline.start": {
          nodes.set(
            event.nodeId,
            makeNode(event.nodeId, "phase", "Pipeline", "active", null, ts),
          );
          jobStatus = "running";
          break;
        }

        case "pipeline.end": {
          const status = event.status === "error" ? "error" : "complete";
          nodes = updateNode(nodes, event.nodeId, {
            status: status as NodeStatus,
            completedAt: ts,
            data: { ...nodes.get(event.nodeId)?.data, error: event.error },
          });
          jobStatus = status === "error" ? "error" : "complete";
          break;
        }

        // ── Ingestion retroactive (emitted by _run_editing) ─────
        case "ingestion.complete": {
          if (!nodes.has("ingestion")) {
            nodes.set(
              "ingestion",
              makeNode("ingestion", "phase", "Ingestion", "complete", event.parentId ?? "pipeline", ts),
            );
          } else {
            nodes = updateNode(nodes, "ingestion", { status: "complete", completedAt: ts });
          }
          const videos = (event.videos ?? []) as Array<{ id: string; filename: string }>;
          for (const v of videos) {
            for (const prefix of ["summary", "asr", "vlm"]) {
              const nid = `${prefix}:${v.id}`;
              if (!nodes.has(nid)) {
                const labels: Record<string, string> = { summary: "Summary", asr: "ASR", vlm: "VLM" };
                nodes.set(
                  nid,
                  makeNode(nid, "phase", `${labels[prefix]} - ${v.filename}`, "complete", "ingestion", ts),
                );
              }
            }
          }
          break;
        }

        // ── Ingestion live stages ───────────────────────────────
        case "ingestion.start": {
          if (!nodes.has(event.nodeId)) {
            nodes.set(
              event.nodeId,
              makeNode(event.nodeId, "phase", "Ingestion", "active", event.parentId ?? "pipeline", ts),
            );
          } else {
            nodes = updateNode(nodes, event.nodeId, { status: "active", startedAt: ts });
          }
          break;
        }

        case "ingestion.end": {
          nodes = updateNode(nodes, event.nodeId, { status: "complete", completedAt: ts });
          break;
        }

        case "summary.start":
        case "asr.start":
        case "vlm.start": {
          const prefix = event.type.split(".")[0];
          const labels: Record<string, string> = { summary: "Summary", asr: "ASR", vlm: "VLM" };
          const label = `${labels[prefix]} - ${event.filename ?? ""}`;

          if (!nodes.has("ingestion")) {
            nodes.set(
              "ingestion",
              makeNode("ingestion", "phase", "Ingestion", "active", "pipeline", ts),
            );
          }
          nodes.set(
            event.nodeId,
            makeNode(event.nodeId, "phase", label, "active", event.parentId ?? "ingestion", ts, {
              videoId: event.videoId,
            }),
          );
          break;
        }

        case "summary.end":
        case "asr.end":
        case "vlm.end": {
          nodes = updateNode(nodes, event.nodeId, {
            status: "complete",
            completedAt: ts,
            data: { ...nodes.get(event.nodeId)?.data, durationS: event.durationS },
          });
          break;
        }

        // ── Agent lifecycle ─────────────────────────────────────
        case "agent.start": {
          const label = prettyLabel(event.name ?? "Agent");
          nodes.set(
            event.nodeId,
            makeNode(event.nodeId, "agent", label, "active", event.parentId ?? "pipeline", ts, {
              maxTurns: event.maxTurns,
            }),
          );
          break;
        }

        case "agent.end": {
          const status = event.status === "error" ? "error" : "complete";
          nodes = updateNode(nodes, event.nodeId, {
            status: status as NodeStatus,
            completedAt: ts,
            data: {
              ...nodes.get(event.nodeId)?.data,
              turns: event.turns,
              summary: event.summary,
              error: event.error,
            },
          });
          break;
        }

        // ── LLM calls (mutate agent node) ───────────────────────
        case "llm.start": {
          nodes = updateNode(nodes, event.nodeId, {
            status: "thinking",
            turn: event.turn ?? 0,
            tokens: "",
            tokenCount: 0,
            data: {
              ...nodes.get(event.nodeId)?.data,
              model: event.model || nodes.get(event.nodeId)?.data.model,
              messageCount: event.messageCount,
              inputChars: event.inputChars,
            },
          });
          break;
        }

        case "llm.chunk": {
          const existing = nodes.get(event.nodeId);
          if (existing) {
            nodes = updateNode(nodes, event.nodeId, {
              tokens: (existing.tokens ?? "") + (event.token ?? ""),
              tokenCount: (existing.tokenCount ?? 0) + 1,
            });
          }
          break;
        }

        case "llm.end": {
          const prev = nodes.get(event.nodeId);
          const prevTotalTokens = (prev?.data.cumulativeTotalTokens as number) ?? 0;
          const prevPrompt = (prev?.data.cumulativePromptTokens as number) ?? 0;
          const prevCompletion = (prev?.data.cumulativeCompletionTokens as number) ?? 0;
          nodes = updateNode(nodes, event.nodeId, {
            status: "active",
            data: {
              ...prev?.data,
              lastContent: event.content,
              hasToolCalls: event.hasToolCalls,
              toolCallCount: event.toolCallCount,
              promptTokens: event.promptTokens,
              completionTokens: event.completionTokens,
              totalTokens: event.totalTokens,
              outputChars: event.outputChars,
              cumulativeTotalTokens: prevTotalTokens + (event.totalTokens ?? 0),
              cumulativePromptTokens: prevPrompt + (event.promptTokens ?? 0),
              cumulativeCompletionTokens: prevCompletion + (event.completionTokens ?? 0),
            },
          });
          break;
        }

        // ── Tool calls (create child nodes of agent) ────────────
        case "tool.start": {
          const label = prettyLabel(event.name ?? "tool");
          nodes.set(
            event.nodeId,
            makeNode(event.nodeId, "tool", label, "active", event.parentId ?? null, ts, {
              toolName: event.name,
              args: event.args,
              toolCallId: event.toolCallId,
            }),
          );
          break;
        }

        case "tool.end": {
          nodes = updateNode(nodes, event.nodeId, {
            status: "complete",
            completedAt: ts,
            data: {
              ...nodes.get(event.nodeId)?.data,
              result: event.result,
            },
          });
          break;
        }

        // ── Render ──────────────────────────────────────────────
        case "render.start": {
          nodes.set(
            event.nodeId,
            makeNode(event.nodeId, "phase", "Rendering", "active", event.parentId ?? "pipeline", ts),
          );
          break;
        }

        case "render.end": {
          nodes = updateNode(nodes, event.nodeId, {
            status: "complete",
            completedAt: ts,
            data: { ...nodes.get(event.nodeId)?.data, outputUri: event.outputUri },
          });
          break;
        }
      }

      return { nodes, jobStatus, lastEventId: event.id };
    }),
}));

const DISPLAY_NAMES: Record<string, string> = {
  planning: "Planning Agent",
  research: "Research Agent",
  clarification: "Clarification Agent",
  user_verification: "User Verification Agent",
  synthesis: "Synthesis Agent",
  remotion_synthesis: "Remotion Synthesis Agent",
  editing_synthesis: "Editing Agent",
  internal_verification: "Verification Agent",
  final_qa: "Final QA Agent",
  editing: "Editing Agent",
};

function prettyLabel(name: string): string {
  if (DISPLAY_NAMES[name]) return DISPLAY_NAMES[name];
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
