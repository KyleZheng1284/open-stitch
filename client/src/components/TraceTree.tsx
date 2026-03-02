import { useCallback, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useReactFlow,
  ReactFlowProvider,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useAutoLayout } from "../hooks/useAutoLayout";
import PhaseNode from "./nodes/PhaseNode";
import AgentNode from "./nodes/AgentNode";
import ToolNode from "./nodes/ToolNode";
import CollapsedNode from "./nodes/CollapsedNode";

const nodeTypes: NodeTypes = {
  phase: PhaseNode,
  agent: AgentNode,
  tool: ToolNode,
  collapsed: CollapsedNode,
};

function TraceTreeInner() {
  const { nodes, edges } = useAutoLayout();
  const { fitView } = useReactFlow();
  const prevCount = useRef(0);

  const handleNodesChange = useCallback(() => {
    if (nodes.length !== prevCount.current) {
      prevCount.current = nodes.length;
      requestAnimationFrame(() => fitView({ padding: 0.25, duration: 300 }));
    }
  }, [nodes.length, fitView]);

  useEffect(handleNodesChange, [handleNodesChange]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={false}
      nodesConnectable={false}
      panOnDrag
      zoomOnScroll
      minZoom={0.3}
      maxZoom={1.5}
    >
      <Background color="#262626" gap={20} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export default function TraceTree() {
  return (
    <ReactFlowProvider>
      <TraceTreeInner />
    </ReactFlowProvider>
  );
}
