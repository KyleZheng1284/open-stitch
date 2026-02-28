"use client";

import React, { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { VideoNode } from "./VideoNode";
import { AgentNode } from "./AgentNode";
import { ToolNode } from "./ToolNode";
import { buildGraphLayout } from "./graph-layout";

const nodeTypes = {
  videoNode: VideoNode,
  agentNode: AgentNode,
  toolNode: ToolNode,
};

interface Video {
  id: string;
  filename: string;
  duration_ms: number;
  thumbnail_url?: string;
  ingestion_status: string;
}

interface AgentState {
  id: string;
  status: "idle" | "running" | "success" | "error";
  progress?: number;
  iteration?: number;
}

interface CanvasPanelProps {
  videos: Video[];
  agentStates: Record<string, AgentState>;
  onVideoReorder: (videoIds: string[]) => void;
}

export const CanvasPanel: React.FC<CanvasPanelProps> = ({
  videos,
  agentStates,
  onVideoReorder,
}) => {
  const { initialNodes, initialEdges } = useMemo(
    () => buildGraphLayout(videos, agentStates),
    [videos, agentStates]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={2}
        defaultEdgeOptions={{
          animated: false,
          style: { stroke: "#2a2d3a", strokeWidth: 2 },
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1a1d27" />
        <Controls className="!bg-canvas-surface !border-canvas-border" />
        <MiniMap
          className="!bg-canvas-surface !border-canvas-border"
          nodeColor={(node) => {
            switch (node.type) {
              case "videoNode":
                return "#3b82f6";
              case "agentNode":
                return "#22c55e";
              case "toolNode":
                return "#f59e0b";
              default:
                return "#6b7280";
            }
          }}
        />
      </ReactFlow>
    </div>
  );
};
