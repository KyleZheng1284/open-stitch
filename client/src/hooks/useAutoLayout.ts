import { useMemo } from "react";
import dagre from "dagre";
import type { Node, Edge } from "@xyflow/react";
import { useTraceStore } from "../stores/traceStore";
import type { NodeKind, TraceNode } from "../types/trace";

const NODE_SIZES: Record<NodeKind | "collapsed", { w: number; h: number }> = {
  phase: { w: 200, h: 52 },
  agent: { w: 240, h: 92 },
  tool: { w: 200, h: 48 },
  collapsed: { w: 160, h: 40 },
};

const COLLAPSE_THRESHOLD = 5;
const VISIBLE_WHEN_COLLAPSED = 3;

/**
 * Convert the flat TraceNode map into positioned ReactFlow Nodes + Edges.
 *
 * When a parent has more than COLLAPSE_THRESHOLD children, only the first
 * few are shown plus a "+N more" placeholder that can be clicked to expand.
 * Tool nodes that share a parent are chained vertically.
 */
export function useAutoLayout(): { nodes: Node[]; edges: Edge[] } {
  const traceNodes = useTraceStore((s) => s.nodes);
  const expandedGroups = useTraceStore((s) => s.expandedGroups);

  return useMemo(() => {
    if (traceNodes.size === 0) return { nodes: [], edges: [] };

    const childrenByParent = new Map<string, string[]>();
    for (const [id, node] of traceNodes) {
      if (node.parentId) {
        const list = childrenByParent.get(node.parentId) ?? [];
        list.push(id);
        childrenByParent.set(node.parentId, list);
      }
    }

    const hiddenIds = new Set<string>();
    const collapsedPlaceholders = new Map<string, { parentId: string; hiddenCount: number }>();

    for (const [parentId, childIds] of childrenByParent) {
      const nonToolChildren = childIds.filter(
        (id) => traceNodes.get(id)?.kind !== "tool"
      );
      if (nonToolChildren.length > COLLAPSE_THRESHOLD && !expandedGroups.has(parentId)) {
        const toHide = nonToolChildren.slice(VISIBLE_WHEN_COLLAPSED);
        for (const id of toHide) hiddenIds.add(id);
        const placeholderId = `_collapsed:${parentId}`;
        collapsedPlaceholders.set(placeholderId, {
          parentId,
          hiddenCount: toHide.length,
        });
      }
    }

    const g = new dagre.graphlib.Graph();
    g.setGraph({
      rankdir: "TB",
      nodesep: 16,
      ranksep: 36,
      marginx: 30,
      marginy: 30,
    });
    g.setDefaultEdgeLabel(() => ({}));

    const toolsByParent = new Map<string, string[]>();
    for (const [id, node] of traceNodes) {
      if (hiddenIds.has(id)) continue;
      if (node.kind === "tool" && node.parentId) {
        if (hiddenIds.has(node.parentId)) continue;
        const list = toolsByParent.get(node.parentId) ?? [];
        list.push(id);
        toolsByParent.set(node.parentId, list);
      }
    }

    for (const [id, node] of traceNodes) {
      if (hiddenIds.has(id)) continue;
      const size = NODE_SIZES[node.kind];
      g.setNode(id, { width: size.w, height: size.h });
    }

    for (const [placeholderId] of collapsedPlaceholders) {
      const size = NODE_SIZES.collapsed;
      g.setNode(placeholderId, { width: size.w, height: size.h });
    }

    const layoutEdges: Array<{ source: string; target: string }> = [];
    for (const [id, node] of traceNodes) {
      if (hiddenIds.has(id)) continue;
      if (node.kind === "tool" && node.parentId) continue;
      if (node.parentId && traceNodes.has(node.parentId) && !hiddenIds.has(node.parentId)) {
        g.setEdge(node.parentId, id);
        layoutEdges.push({ source: node.parentId, target: id });
      }
    }

    for (const [placeholderId, info] of collapsedPlaceholders) {
      g.setEdge(info.parentId, placeholderId);
      layoutEdges.push({ source: info.parentId, target: placeholderId });
    }

    for (const [parentId, toolIds] of toolsByParent) {
      if (toolIds.length === 0) continue;
      g.setEdge(parentId, toolIds[0]);
      layoutEdges.push({ source: parentId, target: toolIds[0] });
      for (let i = 1; i < toolIds.length; i++) {
        g.setEdge(toolIds[i - 1], toolIds[i]);
        layoutEdges.push({ source: toolIds[i - 1], target: toolIds[i] });
      }
    }

    dagre.layout(g);

    const rfNodes: Node[] = [];
    const rfEdges: Edge[] = [];

    for (const [id, node] of traceNodes) {
      if (hiddenIds.has(id)) continue;
      const pos = g.node(id);
      if (!pos) continue;
      rfNodes.push({
        id,
        type: node.kind,
        position: { x: pos.x - pos.width / 2, y: pos.y - pos.height / 2 },
        data: node as unknown as Record<string, unknown>,
      });
    }

    for (const [placeholderId, info] of collapsedPlaceholders) {
      const pos = g.node(placeholderId);
      if (!pos) continue;
      rfNodes.push({
        id: placeholderId,
        type: "collapsed",
        position: { x: pos.x - pos.width / 2, y: pos.y - pos.height / 2 },
        data: {
          parentId: info.parentId,
          hiddenCount: info.hiddenCount,
        },
      });
    }

    for (const edge of layoutEdges) {
      const targetNode = traceNodes.get(edge.target);
      rfEdges.push({
        id: `${edge.source}->${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: targetNode?.status === "active" || targetNode?.status === "thinking",
        style: { stroke: "#404040", strokeWidth: 1.5 },
      });
    }

    return { nodes: rfNodes, edges: rfEdges };
  }, [traceNodes, expandedGroups]);
}
