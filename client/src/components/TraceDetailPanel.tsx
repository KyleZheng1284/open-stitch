import { X, Zap, Clock, Hash, MessageSquare, Cpu, FileText } from "lucide-react";
import { motion } from "motion/react";
import { useTraceStore } from "../stores/traceStore";

export default function TraceDetailPanel() {
  const selectedNodeId = useTraceStore((s) => s.selectedNodeId);
  const nodes = useTraceStore((s) => s.nodes);
  const selectNode = useTraceStore((s) => s.selectNode);

  const node = selectedNodeId ? nodes.get(selectedNodeId) : null;
  if (!node) return null;

  const elapsed =
    node.startedAt && node.completedAt
      ? (node.completedAt - node.startedAt).toFixed(2)
      : null;

  return (
    <motion.aside
      initial={{ x: 380 }}
      animate={{ x: 0 }}
      exit={{ x: 380 }}
      transition={{ type: "spring", damping: 25, stiffness: 300 }}
      className="w-[380px] h-full border-l border-neutral-800 bg-neutral-900 flex flex-col overflow-hidden shrink-0"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
        <div className="flex items-center gap-2 min-w-0">
          <Badge status={node.status} />
          <h3 className="text-sm font-semibold text-neutral-100 truncate">
            {node.label}
          </h3>
        </div>
        <button
          onClick={() => selectNode(null)}
          className="p-1 rounded hover:bg-neutral-800 text-neutral-400 hover:text-neutral-100 transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-xs">
        {/* Quick stats row */}
        <div className="flex flex-wrap gap-2">
          {elapsed && <Stat icon={Clock} label="Duration" value={`${elapsed}s`} />}
          {node.kind === "agent" && node.turn > 0 && (
            <Stat icon={Hash} label="Turns" value={String(node.turn)} />
          )}
          {node.kind === "agent" && typeof node.data.cumulativeTotalTokens === "number" && (node.data.cumulativeTotalTokens as number) > 0 && (
            <Stat icon={Zap} label="Total Tokens" value={(node.data.cumulativeTotalTokens as number).toLocaleString()} />
          )}
          {node.kind === "agent" && typeof node.data.cumulativePromptTokens === "number" && (node.data.cumulativePromptTokens as number) > 0 && (
            <Stat icon={FileText} label="Prompt Tokens" value={(node.data.cumulativePromptTokens as number).toLocaleString()} />
          )}
          {node.kind === "agent" && typeof node.data.cumulativeCompletionTokens === "number" && (node.data.cumulativeCompletionTokens as number) > 0 && (
            <Stat icon={Zap} label="Completion Tokens" value={(node.data.cumulativeCompletionTokens as number).toLocaleString()} />
          )}
          {node.kind === "agent" && typeof node.data.messageCount === "number" && (
            <Stat icon={MessageSquare} label="Messages" value={String(node.data.messageCount)} />
          )}
          {node.kind === "agent" && typeof node.data.model === "string" && (node.data.model as string).length > 0 && (
            <Stat icon={Cpu} label="Model" value={String(node.data.model)} />
          )}
          {node.tokenCount > 0 && (
            <Stat icon={Zap} label="Streamed Chunks" value={String(node.tokenCount)} />
          )}
        </div>

        {/* Node ID */}
        <Section title="Node ID">
          <code className="text-[11px] text-neutral-400 font-mono break-all">{node.id}</code>
        </Section>

        {/* Agent: LLM output (live tokens) */}
        {node.kind === "agent" && node.tokens.length > 0 && (
          <Section title="LLM Output (live)">
            <pre className="whitespace-pre-wrap text-neutral-300 bg-neutral-950 rounded-lg p-3 max-h-60 overflow-y-auto font-mono text-[11px] leading-relaxed">
              {node.tokens}
            </pre>
          </Section>
        )}

        {/* Agent: last content from llm.end */}
        {node.kind === "agent" && typeof node.data.lastContent === "string" && (node.data.lastContent as string).length > 0 && (
          <Section title="Last LLM Response">
            <pre className="whitespace-pre-wrap text-neutral-300 bg-neutral-950 rounded-lg p-3 max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed">
              {String(node.data.lastContent)}
            </pre>
          </Section>
        )}

        {/* Agent: per-turn stats */}
        {node.kind === "agent" && typeof node.data.totalTokens === "number" && (
          <Section title="Last Turn Stats">
            <div className="grid grid-cols-2 gap-2">
              <MiniStat label="Prompt Tok" value={String(node.data.promptTokens ?? 0)} />
              <MiniStat label="Completion Tok" value={String(node.data.completionTokens ?? 0)} />
              <MiniStat label="Total Tok" value={String(node.data.totalTokens ?? 0)} />
              <MiniStat label="Tool Calls" value={String(node.data.toolCallCount ?? 0)} />
            </div>
          </Section>
        )}

        {/* Agent: summary */}
        {node.kind === "agent" && typeof node.data.summary === "string" && (
          <Section title="Agent Summary">
            <p className="text-neutral-300 leading-relaxed">{String(node.data.summary)}</p>
          </Section>
        )}

        {/* Tool: arguments */}
        {node.kind === "tool" && node.data.args != null && (
          <Section title="Tool Arguments">
            <JsonBlock value={node.data.args} />
          </Section>
        )}

        {/* Tool: result */}
        {node.kind === "tool" && node.data.result != null && (
          <Section title="Tool Result">
            <JsonBlock value={node.data.result} />
          </Section>
        )}

        {/* Tool: meta */}
        {node.kind === "tool" && typeof node.data.toolCallId === "string" && (
          <Section title="Tool Call ID">
            <code className="text-[11px] text-neutral-400 font-mono break-all">
              {String(node.data.toolCallId)}
            </code>
          </Section>
        )}

        {/* Phase: video info */}
        {node.kind === "phase" && typeof node.data.videoId === "string" && (
          <Section title="Video">
            <span className="text-neutral-300">{String(node.data.videoId)}</span>
          </Section>
        )}

        {node.kind === "phase" && typeof node.data.outputUri === "string" && (
          <Section title="Output Path">
            <code className="text-[11px] text-neutral-300 font-mono break-all">
              {String(node.data.outputUri)}
            </code>
          </Section>
        )}

        {node.kind === "phase" && typeof node.data.error === "string" && (
          <Section title="Error">
            <pre className="whitespace-pre-wrap text-red-400 bg-red-500/10 rounded-lg p-3 font-mono text-[11px]">
              {String(node.data.error)}
            </pre>
          </Section>
        )}

        {/* Raw data dump */}
        <Section title="Raw Event Data">
          <JsonBlock value={node.data} />
        </Section>
      </div>
    </motion.aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1.5 font-medium">
        {title}
      </h4>
      <div>{children}</div>
    </div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Zap; label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-800/60 rounded-lg">
      <Icon className="w-3 h-3 text-neutral-500 shrink-0" />
      <span className="text-[10px] text-neutral-500">{label}</span>
      <span className="text-[11px] text-neutral-200 font-medium ml-auto">{value}</span>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-neutral-800/40 rounded px-2 py-1.5">
      <div className="text-[9px] text-neutral-500 uppercase">{label}</div>
      <div className="text-[11px] text-neutral-200 font-medium">{value}</div>
    </div>
  );
}

function Badge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-neutral-700 text-neutral-400",
    active: "bg-blue-500/20 text-blue-400",
    thinking: "bg-blue-500/20 text-blue-400",
    complete: "bg-green-600/20 text-green-400",
    error: "bg-red-500/20 text-red-400",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium shrink-0 ${colors[status] ?? colors.pending}`}
    >
      {status}
    </span>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  let formatted: string;
  try {
    formatted =
      typeof value === "string"
        ? tryParseAndFormat(value)
        : JSON.stringify(value, null, 2);
  } catch {
    formatted = String(value);
  }

  return (
    <pre className="whitespace-pre-wrap text-neutral-300 bg-neutral-950 rounded-lg p-3 max-h-56 overflow-y-auto font-mono text-[11px] leading-relaxed">
      {formatted}
    </pre>
  );
}

function tryParseAndFormat(s: string): string {
  try {
    return JSON.stringify(JSON.parse(s), null, 2);
  } catch {
    return s;
  }
}
