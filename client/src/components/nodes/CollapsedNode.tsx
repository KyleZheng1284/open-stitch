import { Handle, Position, type NodeProps } from "@xyflow/react";
import { ChevronDown } from "lucide-react";
import { useTraceStore } from "../../stores/traceStore";

export default function CollapsedNode({ data }: NodeProps) {
  const info = data as unknown as { parentId: string; hiddenCount: number };
  const toggleGroup = useTraceStore((s) => s.toggleGroup);

  return (
    <div
      onClick={() => toggleGroup(info.parentId)}
      className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-dashed border-neutral-600 bg-neutral-900 cursor-pointer hover:border-neutral-400 transition-colors min-w-[140px]"
    >
      <ChevronDown className="w-3.5 h-3.5 text-neutral-500" />
      <span className="text-xs text-neutral-400">
        +{info.hiddenCount} more
      </span>
      <Handle type="target" position={Position.Top} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
      <Handle type="source" position={Position.Bottom} className="!bg-neutral-600 !w-2 !h-2 !border-0" />
    </div>
  );
}
