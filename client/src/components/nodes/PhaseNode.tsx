import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Layers,
  Database,
  FileVideo,
  Mic,
  Eye,
  Film,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { useTraceStore } from "../../stores/traceStore";
import type { TraceNode } from "../../types/trace";

const ICON_MAP: Record<string, typeof Layers> = {
  Pipeline: Layers,
  Ingestion: Database,
  Summary: FileVideo,
  ASR: Mic,
  VLM: Eye,
  Rendering: Film,
};

function getIcon(label: string) {
  for (const [key, Icon] of Object.entries(ICON_MAP)) {
    if (label.startsWith(key)) return Icon;
  }
  return Layers;
}

const BORDER: Record<string, string> = {
  pending: "border-neutral-700",
  active: "border-blue-500",
  thinking: "border-blue-500",
  complete: "border-green-600",
  error: "border-red-500",
};

export default function PhaseNode({ data, id }: NodeProps) {
  const node = data as unknown as TraceNode;
  const selectNode = useTraceStore((s) => s.selectNode);
  const selectedNodeId = useTraceStore((s) => s.selectedNodeId);
  const Icon = getIcon(node.label);
  const isSelected = selectedNodeId === id;

  const elapsed =
    node.startedAt && node.completedAt
      ? (node.completedAt - node.startedAt).toFixed(1)
      : null;

  return (
    <div
      onClick={() => selectNode(isSelected ? null : id)}
      className={`
        flex items-center gap-2.5 px-4 py-2.5 rounded-xl border bg-neutral-900
        min-w-[180px] cursor-pointer transition-all duration-200
        ${isSelected ? "border-blue-500 ring-1 ring-blue-500/30" : BORDER[node.status] ?? "border-neutral-700"}
        ${!isSelected ? "hover:border-neutral-500" : ""}
      `}
    >
      <Icon className="w-4 h-4 shrink-0 text-neutral-400" />
      <span className="text-sm font-medium text-neutral-100 truncate">
        {node.label}
      </span>
      <div className="ml-auto flex items-center gap-1.5 shrink-0">
        {elapsed && node.status === "complete" && (
          <span className="text-[10px] text-neutral-500">{elapsed}s</span>
        )}
        {node.status === "active" || node.status === "thinking" ? (
          <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
        ) : node.status === "complete" ? (
          <CheckCircle2 className="w-4 h-4 text-green-500" />
        ) : node.status === "error" ? (
          <XCircle className="w-4 h-4 text-red-500" />
        ) : null}
      </div>
      <Handle type="target" position={Position.Top} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
      <Handle type="source" position={Position.Bottom} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
    </div>
  );
}
