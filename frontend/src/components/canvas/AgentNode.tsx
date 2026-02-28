"use client";

import React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

interface AgentNodeData {
  label: string;
  status: "idle" | "running" | "success" | "error";
  iteration?: number;
  maxIterations?: number;
  [key: string]: unknown;
}

const statusColors = {
  idle: "border-gray-600 bg-canvas-surface",
  running: "border-blue-500 bg-canvas-surface animate-pulse-border",
  success: "border-green-500 bg-canvas-surface",
  error: "border-red-500 bg-canvas-surface",
};

const statusIcons = {
  idle: "⬡",
  running: "⟳",
  success: "✓",
  error: "✕",
};

/**
 * Custom React Flow node for agent pipeline stages.
 * Rounded box, larger, with color-coded status and iteration counter.
 */
export const AgentNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as AgentNodeData;

  return (
    <div
      className={`rounded-xl border-2 px-4 py-3 min-w-[160px] ${statusColors[d.status]}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-canvas-accent" />

      <div className="flex items-center gap-2">
        <span className="text-sm">{statusIcons[d.status]}</span>
        <span className="text-sm font-semibold">{d.label}</span>
      </div>

      {d.iteration !== undefined && (
        <div className="text-[10px] text-gray-400 mt-1">
          iter {d.iteration}/{d.maxIterations || 3}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-canvas-accent" />
    </div>
  );
};
