/** Wire format from SSE -- every event has these base fields. */
export interface TraceEvent {
  id: string;
  type: string;
  ts: number;
  nodeId: string;
  parentId?: string | null;

  name?: string;
  args?: Record<string, unknown>;
  result?: string;
  content?: string;
  token?: string;
  text?: string;
  turn?: number;
  hasToolCalls?: boolean;
  toolCallId?: string;
  toolCallCount?: number;
  messageCount?: number;
  maxTurns?: number;
  turns?: number;
  summary?: string;
  status?: string;
  error?: string;
  videos?: Array<{ id: string; filename: string }>;
  videoId?: string;
  filename?: string;
  durationS?: number;
  outputUri?: string;
  inputChars?: number;
  outputChars?: number;
  outputTokens?: number;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  model?: string;
  [key: string]: unknown;
}

export type NodeStatus =
  | "pending"
  | "active"
  | "thinking"
  | "complete"
  | "error";

export type NodeKind = "phase" | "agent" | "tool";

export interface TraceNode {
  id: string;
  kind: NodeKind;
  label: string;
  status: NodeStatus;
  parentId: string | null;
  startedAt: number | null;
  completedAt: number | null;
  turn: number;
  maxTurns: number | null;
  tokens: string;
  tokenCount: number;
  data: Record<string, unknown>;
}
