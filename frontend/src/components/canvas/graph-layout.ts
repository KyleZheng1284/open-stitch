/**
 * Graph layout builder for the React Flow canvas.
 *
 * Generates node and edge definitions for:
 * 1. Video sequence nodes (top zone, connected in order)
 * 2. Agent pipeline nodes (bottom zone, showing processing stages)
 * 3. Tool nodes (attached to parent agents)
 */

import type { Node, Edge } from "@xyflow/react";

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

const AGENT_PIPELINE = [
  { id: "react-loop", label: "ReAct Loop", hasIteration: true },
  { id: "subtitle", label: "Subtitle Agent" },
  { id: "music", label: "Music Agent" },
  { id: "meme-sfx", label: "Meme/SFX Agent" },
  { id: "assembly", label: "Assembly" },
  { id: "publishing", label: "Publishing" },
];

export function buildGraphLayout(
  videos: Video[],
  agentStates: Record<string, AgentState>
): { initialNodes: Node[]; initialEdges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const videoStartX = 100;
  const videoY = 50;
  const videoSpacingX = 220;

  // ─── Video Nodes ────────────────────────────────────────────────
  videos.forEach((video, idx) => {
    nodes.push({
      id: `video-${video.id}`,
      type: "videoNode",
      position: { x: videoStartX + idx * videoSpacingX, y: videoY },
      data: {
        filename: video.filename,
        duration_ms: video.duration_ms,
        thumbnail_url: video.thumbnail_url,
        ingestion_status: video.ingestion_status,
      },
    });

    // Chain videos with edges
    if (idx > 0) {
      edges.push({
        id: `video-edge-${idx}`,
        source: `video-${videos[idx - 1].id}`,
        target: `video-${video.id}`,
        animated: false,
      });
    }
  });

  // ─── Agent Pipeline Nodes ───────────────────────────────────────
  const agentY = 250;
  const agentStartX = 100;

  // ReAct Loop (centered below videos)
  const reactState = agentStates["react-loop"];
  nodes.push({
    id: "agent-react-loop",
    type: "agentNode",
    position: { x: agentStartX + 200, y: agentY },
    data: {
      label: "ReAct Loop",
      status: reactState?.status || "idle",
      iteration: reactState?.iteration,
      maxIterations: 3,
    },
  });

  // Connect last video to ReAct loop
  if (videos.length > 0) {
    edges.push({
      id: "video-to-react",
      source: `video-${videos[videos.length - 1].id}`,
      target: "agent-react-loop",
      animated: true,
    });
  }

  // Parallel post-processing agents
  const parallelAgents = ["subtitle", "music", "meme-sfx"];
  parallelAgents.forEach((agentId, idx) => {
    const state = agentStates[agentId];
    const agent = AGENT_PIPELINE.find((a) => a.id === agentId)!;
    nodes.push({
      id: `agent-${agentId}`,
      type: "agentNode",
      position: { x: agentStartX + idx * 200, y: agentY + 120 },
      data: {
        label: agent.label,
        status: state?.status || "idle",
      },
    });

    // Connect from ReAct loop
    edges.push({
      id: `react-to-${agentId}`,
      source: "agent-react-loop",
      target: `agent-${agentId}`,
    });
  });

  // Assembly agent
  const assemblyState = agentStates["assembly"];
  nodes.push({
    id: "agent-assembly",
    type: "agentNode",
    position: { x: agentStartX + 200, y: agentY + 240 },
    data: {
      label: "Assembly",
      status: assemblyState?.status || "idle",
    },
  });

  parallelAgents.forEach((agentId) => {
    edges.push({
      id: `${agentId}-to-assembly`,
      source: `agent-${agentId}`,
      target: "agent-assembly",
    });
  });

  // Publishing agent
  const pubState = agentStates["publishing"];
  nodes.push({
    id: "agent-publishing",
    type: "agentNode",
    position: { x: agentStartX + 200, y: agentY + 360 },
    data: {
      label: "Publishing",
      status: pubState?.status || "idle",
    },
  });

  edges.push({
    id: "assembly-to-publishing",
    source: "agent-assembly",
    target: "agent-publishing",
  });

  return { initialNodes: nodes, initialEdges: edges };
}
