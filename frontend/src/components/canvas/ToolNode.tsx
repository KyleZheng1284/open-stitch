"use client";

import React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

interface ToolNodeData {
  label: string;
  status: "idle" | "running" | "success" | "error";
  latency_ms?: number;
  [key: string]: unknown;
}

/**
 * Custom React Flow node for tool invocations.
 * Smaller, dashed border, connected to parent agent.
 */
export const ToolNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as ToolNodeData;

  return (
    <div className="rounded-md border border-dashed border-canvas-border bg-canvas-bg px-3 py-2 min-w-[120px]">
      <Handle type="target" position={Position.Top} className="!bg-gray-500 !w-2 !h-2" />

      <div className="text-[11px] font-mono text-gray-300">{d.label}</div>

      {d.latency_ms !== undefined && (
        <div className="text-[9px] text-gray-500 mt-0.5">
          {d.latency_ms}ms
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-gray-500 !w-2 !h-2" />
    </div>
  );
};
