import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Bot, CheckCircle2, XCircle, Zap } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useTraceStore } from "../../stores/traceStore";
import type { TraceNode } from "../../types/trace";

const BORDER: Record<string, string> = {
  pending: "border-neutral-700",
  active: "border-blue-500 ring-1 ring-blue-500/20",
  thinking: "border-blue-400 ring-1 ring-blue-400/30",
  complete: "border-green-600",
  error: "border-red-500",
};

export default function AgentNode({ data, id }: NodeProps) {
  const node = data as unknown as TraceNode;
  const selectNode = useTraceStore((s) => s.selectNode);
  const selectedNodeId = useTraceStore((s) => s.selectedNodeId);
  const maxTurns = node.maxTurns ?? (node.data.maxTurns as number | null);
  const isSelected = selectedNodeId === id;
  const totalTokens = (node.data.cumulativeTotalTokens as number) ?? 0;
  const model = (node.data.model as string) ?? "";
  const shortModel = model.split("/").pop() ?? model;

  return (
    <div
      onClick={() => selectNode(isSelected ? null : id)}
      className={`
        relative flex flex-col gap-1.5 px-5 py-3.5 rounded-xl border bg-neutral-900
        min-w-[220px] cursor-pointer transition-all duration-200
        ${isSelected ? "border-blue-500 ring-1 ring-blue-500/30" : BORDER[node.status] ?? "border-neutral-700"}
        ${!isSelected ? "hover:border-neutral-500" : ""}
      `}
    >
      <div className="flex items-center gap-2.5">
        <Bot className="w-5 h-5 shrink-0 text-blue-400" />
        <span className="text-sm font-semibold text-neutral-100">
          {node.label}
        </span>
        <div className="ml-auto shrink-0">
          {node.status === "complete" ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : node.status === "error" ? (
            <XCircle className="w-4 h-4 text-red-500" />
          ) : null}
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-neutral-400">
        <AnimatePresence mode="wait">
          {node.status === "thinking" ? (
            <motion.span
              key="thinking"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-blue-400"
            >
              <span className="inline-flex items-center gap-0.5">
                Thinking
                <span className="inline-flex w-4">
                  <span className="animate-pulse">.</span>
                  <span className="animate-pulse [animation-delay:150ms]">.</span>
                  <span className="animate-pulse [animation-delay:300ms]">.</span>
                </span>
              </span>
            </motion.span>
          ) : node.status === "complete" ? (
            <motion.span
              key="done"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2"
            >
              <span>{node.turn} turn{node.turn !== 1 ? "s" : ""}</span>
              {totalTokens > 0 && (
                <span className="flex items-center gap-0.5 text-neutral-500">
                  <Zap className="w-3 h-3" />
                  {totalTokens.toLocaleString()} tok
                </span>
              )}
            </motion.span>
          ) : node.turn > 0 ? (
            <motion.span
              key="turn"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2"
            >
              <span>Turn {node.turn}{maxTurns ? ` / ${maxTurns}` : ""}</span>
              {totalTokens > 0 && (
                <span className="flex items-center gap-0.5 text-neutral-500">
                  <Zap className="w-3 h-3" />
                  {totalTokens.toLocaleString()}
                </span>
              )}
            </motion.span>
          ) : null}
        </AnimatePresence>
      </div>

      {shortModel && (
        <div className="text-[10px] text-neutral-600 truncate">{shortModel}</div>
      )}

      <Handle type="target" position={Position.Top} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
      <Handle type="source" position={Position.Bottom} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
    </div>
  );
}
