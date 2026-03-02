import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Film,
  Type,
  Image,
  Music,
  Search,
  List,
  BarChart3,
  Wrench,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { useTraceStore } from "../../stores/traceStore";
import type { TraceNode } from "../../types/trace";

const TOOL_ICONS: Record<string, typeof Wrench> = {
  add_clip: Film,
  add_subtitle: Type,
  add_overlay: Image,
  add_audio: Music,
  search_and_download_asset: Search,
  list_available_assets: List,
  get_composition_state: BarChart3,
};

const ACCENT: Record<string, string> = {
  active: "bg-amber-500",
  thinking: "bg-amber-500",
  complete: "bg-green-500",
  error: "bg-red-500",
  pending: "bg-neutral-600",
};

function summarizeArgs(toolName: string, args: Record<string, unknown> | undefined): string {
  if (!args) return "";
  switch (toolName) {
    case "add_clip":
      return `${args.source_video} [${args.start_s}s-${args.end_s}s]`;
    case "add_subtitle":
      return `"${String(args.text ?? "").slice(0, 30)}..."`;
    case "add_overlay":
      return String(args.asset_path ?? "").split("/").pop() ?? "";
    case "add_audio": {
      const path = String(args.asset_path ?? "").split("/").pop() ?? "";
      const vol = args.volume != null ? ` vol=${args.volume}` : "";
      return `${path}${vol}`;
    }
    case "search_and_download_asset":
      return `"${args.query}" (${args.category})`;
    case "list_available_assets":
      return String(args.category ?? "");
    default:
      return "";
  }
}

function formatDuration(startedAt: number | null, completedAt: number | null): string | null {
  if (!startedAt || !completedAt) return null;
  const ms = (completedAt - startedAt) * 1000;
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function ToolNode({ data, id }: NodeProps) {
  const node = data as unknown as TraceNode;
  const selectNode = useTraceStore((s) => s.selectNode);
  const selectedNodeId = useTraceStore((s) => s.selectedNodeId);

  const toolName = (node.data.toolName as string) ?? "";
  const Icon = TOOL_ICONS[toolName] ?? Wrench;
  const isSelected = selectedNodeId === id;
  const elapsed = formatDuration(node.startedAt, node.completedAt);
  const summary = summarizeArgs(toolName, node.data.args as Record<string, unknown> | undefined);

  return (
    <div
      onClick={(e) => { e.stopPropagation(); selectNode(isSelected ? null : id); }}
      className={`
        relative flex items-center gap-1.5 pl-0 pr-3 py-2 rounded-lg border bg-neutral-900
        w-[200px] cursor-pointer transition-all duration-200 overflow-hidden
        ${isSelected ? "border-blue-500 ring-1 ring-blue-500/30" : "border-neutral-700 hover:border-neutral-500"}
      `}
    >
      <div className={`w-1 self-stretch rounded-l-lg shrink-0 ${ACCENT[node.status] ?? "bg-neutral-600"}`} />

      <Icon className="w-3.5 h-3.5 shrink-0 text-neutral-400" />

      <div className="flex flex-col min-w-0 flex-1">
        <div className="flex items-center gap-1">
          <span className="text-[11px] font-medium text-neutral-200 truncate">
            {node.label}
          </span>
          {elapsed && node.status === "complete" && (
            <span className="text-[9px] text-neutral-500 shrink-0">{elapsed}</span>
          )}
        </div>
        {summary && (
          <span className="text-[9px] text-neutral-500 truncate leading-tight">
            {summary}
          </span>
        )}
      </div>

      <div className="shrink-0">
        {node.status === "active" ? (
          <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" />
        ) : node.status === "complete" ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
        ) : node.status === "error" ? (
          <XCircle className="w-3.5 h-3.5 text-red-500" />
        ) : null}
      </div>

      <Handle type="target" position={Position.Top} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
      <Handle type="source" position={Position.Bottom} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
    </div>
  );
}
