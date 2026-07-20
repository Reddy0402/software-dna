/**
 * Transform backend API data into React Flow nodes and edges.
 */
import type { Node, Edge } from '@xyflow/react';
import type { GraphNode, GraphEdge, EntityType, RelationshipType } from '../types/graph';
import { getEntityColor, getRelationshipColor } from './colors';

/**
 * Convert a backend GraphNode into a React Flow Node.
 */
export function toFlowNode(
  node: GraphNode,
  isHighlighted = false,
  isSelected = false,
): Node {
  const colors = getEntityColor(node.entity_type);

  return {
    id: node.id,
    type: 'entityNode',
    position: { x: 0, y: 0 }, // will be set by layout engine
    data: {
      label: node.name || node.label,
      entityType: node.entity_type,
      fqn: node.fully_qualified_name,
      language: node.language,
      filePath: node.file_path,
      startLine: node.start_line,
      endLine: node.end_line,
      visibility: node.visibility,
      icon: colors.icon,
      color: colors.primary,
      gradient: colors.gradient,
      borderColor: colors.border,
      glowColor: colors.glow,
      bgColor: colors.bgOpacity,
      isHighlighted,
      isSelected,
    },
  };
}

/**
 * Convert a backend GraphEdge into a React Flow Edge.
 */
export function toFlowEdge(edge: GraphEdge): Edge {
  const color = getRelationshipColor(edge.relationship_type);
  const isStructural = ['DEFINED_IN', 'BELONGS_TO', 'CONTAINS', 'DEFINES'].includes(
    edge.relationship_type,
  );

  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: !isStructural,
    label: edge.relationship_type,
    style: {
      stroke: color,
      strokeWidth: isStructural ? 1 : 2,
      opacity: isStructural ? 0.4 : 0.8,
    },
    labelStyle: {
      fill: color,
      fontSize: 10,
      fontWeight: 500,
    },
    labelBgStyle: {
      fill: '#0f172a',
      fillOpacity: 0.85,
    },
    labelBgPadding: [4, 2] as [number, number],
    markerEnd: {
      type: 'arrowclosed' as const,
      color,
      width: 16,
      height: 16,
    },
    data: {
      relationshipType: edge.relationship_type,
      confidence: edge.confidence,
    },
  };
}

/**
 * Convert arrays of GraphNode/GraphEdge into React Flow format.
 */
export function transformGraphData(
  nodes: GraphNode[],
  edges: GraphEdge[],
  highlightedIds: Set<string> = new Set(),
  selectedId: string | null = null,
  nodeTypeFilter: EntityType[] = [],
  relTypeFilter: RelationshipType[] = [],
): { flowNodes: Node[]; flowEdges: Edge[] } {
  // Apply node type filter
  let filteredNodes = nodes;
  if (nodeTypeFilter.length > 0) {
    filteredNodes = nodes.filter((n) =>
      nodeTypeFilter.includes(n.entity_type as EntityType),
    );
  }

  const visibleIds = new Set(filteredNodes.map((n) => n.id));

  // Apply relationship type filter and only include edges between visible nodes
  let filteredEdges = edges.filter(
    (e) => visibleIds.has(e.source) && visibleIds.has(e.target),
  );
  if (relTypeFilter.length > 0) {
    filteredEdges = filteredEdges.filter((e) =>
      relTypeFilter.includes(e.relationship_type as RelationshipType),
    );
  }

  const flowNodes = filteredNodes.map((n) =>
    toFlowNode(n, highlightedIds.has(n.id), n.id === selectedId),
  );
  const flowEdges = filteredEdges.map(toFlowEdge);

  return { flowNodes, flowEdges };
}
