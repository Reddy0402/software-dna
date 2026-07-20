/**
 * Dagre-based automatic layout engine for the graph.
 * Positions nodes in a hierarchical directed graph layout.
 */
import Dagre from '@dagrejs/dagre';
import type { Node, Edge } from '@xyflow/react';

export type LayoutDirection = 'TB' | 'LR' | 'BT' | 'RL';

interface LayoutOptions {
  direction?: LayoutDirection;
  nodeWidth?: number;
  nodeHeight?: number;
  rankSep?: number;
  nodeSep?: number;
}

export function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
  options: LayoutOptions = {},
): { nodes: Node[]; edges: Edge[] } {
  const {
    direction = 'TB',
    nodeWidth = 220,
    nodeHeight = 80,
    rankSep = 80,
    nodeSep = 40,
  } = options;

  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, ranksep: rankSep, nodesep: nodeSep });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  Dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - nodeWidth / 2,
        y: pos.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

/**
 * Simple radial layout: places nodes in concentric circles
 * around a center node.
 */
export function applyRadialLayout(
  nodes: Node[],
  edges: Edge[],
  centerId?: string,
): { nodes: Node[]; edges: Edge[] } {
  if (nodes.length === 0) return { nodes, edges };

  const center = centerId
    ? nodes.find((n) => n.id === centerId) || nodes[0]
    : nodes[0];

  const otherNodes = nodes.filter((n) => n.id !== center.id);
  const cx = 600;
  const cy = 400;

  const layoutedNodes = nodes.map((node) => {
    if (node.id === center.id) {
      return { ...node, position: { x: cx, y: cy } };
    }
    const idx = otherNodes.indexOf(node);
    const total = otherNodes.length;
    const radius = 200 + Math.floor(idx / 12) * 150;
    const angleStep = (2 * Math.PI) / Math.min(total, 12);
    const ring = Math.floor(idx / 12);
    const posInRing = idx % 12;
    const angle = posInRing * angleStep + ring * 0.3;

    return {
      ...node,
      position: {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}
