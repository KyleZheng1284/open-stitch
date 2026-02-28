"use client";

import React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { StatusDot } from "@/components/common/StatusDot";

interface VideoNodeData {
  filename: string;
  duration_ms: number;
  thumbnail_url?: string;
  ingestion_status: string;
  [key: string]: unknown;
}

/**
 * Custom React Flow node for uploaded videos.
 * Shows thumbnail, filename, duration, and ingestion status.
 * Draggable on the canvas for reordering the video sequence.
 */
export const VideoNode: React.FC<NodeProps> = ({ data }) => {
  const d = data as VideoNodeData;
  const durationStr = `${Math.floor(d.duration_ms / 60000)}:${String(
    Math.floor((d.duration_ms % 60000) / 1000)
  ).padStart(2, "0")}`;

  return (
    <div className="bg-canvas-surface border-2 border-canvas-border rounded-lg p-3 min-w-[180px] hover:border-canvas-accent transition-colors">
      <Handle type="target" position={Position.Top} className="!bg-canvas-accent" />

      {/* Thumbnail */}
      <div className="w-full h-20 bg-gray-800 rounded mb-2 flex items-center justify-center overflow-hidden">
        {d.thumbnail_url ? (
          <img
            src={d.thumbnail_url}
            alt={d.filename}
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-xs text-gray-500">No preview</span>
        )}
      </div>

      {/* Info */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium truncate max-w-[120px]">
          {d.filename}
        </span>
        <span className="text-xs text-gray-400">{durationStr}</span>
      </div>

      {/* Status */}
      <div className="flex items-center gap-1 mt-1">
        <StatusDot status={d.ingestion_status} />
        <span className="text-[10px] text-gray-400">{d.ingestion_status}</span>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-canvas-accent" />
    </div>
  );
};
