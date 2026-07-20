/**
 * Main graph visualization canvas using React Flow.
 * Handles node interaction, layout, and lazy expansion.
 */
import { useCallback, useMemo, useEffect, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  type OnNodeClick,
  Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import EntityNode from './CustomNodes';
import { useGraphStore } from '../../store/graphStore';
import { useGraphData } from '../../hooks/useGraphHooks';
import { transformGraphData } from '../../utils/graphTransforms';
import { applyDagreLayout, applyRadialLayout, type LayoutDirection } from '../../utils/layoutEngine';
import { getEntityColor } from '../../utils/colors';
import type { EntityType, RelationshipType } from '../../types/graph';

const nodeTypes = { entityNode: EntityNode };

export default function GraphCanvas() {
  const {
    nodes: graphNodes,
    edges: graphEdges,
    selectedNodeId,
    setSelectedNodeId,
    setSelectedEntityDetail,
    setDetailPanelOpen,
    highlightedNodeIds,
    filters,
    isLoading,
  } = useGraphStore();

  const { expandNode, loadEntityDetail } = useGraphData();
  const { fitView } = useReactFlow();

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<Node>([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [layoutDirection, setLayoutDirection] = useState<LayoutDirection>('TB');
  const [layoutMode, setLayoutMode] = useState<'dagre' | 'radial'>('dagre');

  // Transform and layout
  const applyLayout = useCallback(() => {
    const { flowNodes: transformed, flowEdges: transformedEdges } = transformGraphData(
      graphNodes,
      graphEdges,
      highlightedNodeIds,
      selectedNodeId,
      filters.nodeTypes as EntityType[],
      filters.relationshipTypes as RelationshipType[],
    );

    if (transformed.length === 0) {
      setFlowNodes([]);
      setFlowEdges([]);
      return;
    }

    let layoutResult;
    if (layoutMode === 'radial') {
      layoutResult = applyRadialLayout(transformed, transformedEdges, selectedNodeId || undefined);
    } else {
      layoutResult = applyDagreLayout(transformed, transformedEdges, { direction: layoutDirection });
    }

    setFlowNodes(layoutResult.nodes);
    setFlowEdges(layoutResult.edges);

    // Fit view after layout with a small delay for animation
    setTimeout(() => fitView({ padding: 0.15, duration: 400 }), 100);
  }, [
    graphNodes, graphEdges, highlightedNodeIds, selectedNodeId,
    filters, layoutDirection, layoutMode, setFlowNodes, setFlowEdges, fitView,
  ]);

  useEffect(() => {
    applyLayout();
  }, [applyLayout]);

  // Node click → show detail panel
  const onNodeClick: OnNodeClick = useCallback(
    async (_event, node) => {
      setSelectedNodeId(node.id);
      setDetailPanelOpen(true);
      const detail = await loadEntityDetail(node.id);
      if (detail) setSelectedEntityDetail(detail);
    },
    [setSelectedNodeId, setDetailPanelOpen, loadEntityDetail, setSelectedEntityDetail],
  );

  // Double-click → expand neighbors
  const onNodeDoubleClick = useCallback(
    async (_event: React.MouseEvent, node: Node) => {
      await expandNode(node.id);
    },
    [expandNode],
  );

  // Pane click → deselect
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setDetailPanelOpen(false);
    setSelectedEntityDetail(null);
  }, [setSelectedNodeId, setDetailPanelOpen, setSelectedEntityDetail]);

  // Minimap node color
  const minimapNodeColor = useCallback((node: Node) => {
    const entityType = (node.data as Record<string, unknown>)?.entityType as string;
    return getEntityColor(entityType || 'unknown').primary;
  }, []);

  return (
    <div className="graph-canvas">
      {isLoading && (
        <div className="graph-canvas__loading">
          <div className="loading-spinner__ring" />
          <span>Loading graph…</span>
        </div>
      )}

      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2.5}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} color="#1e293b" gap={24} size={1} />

        <Controls
          className="graph-controls"
          showInteractive={false}
        />

        <MiniMap
          nodeColor={minimapNodeColor}
          maskColor="rgba(10, 14, 26, 0.85)"
          className="graph-minimap"
          pannable
          zoomable
        />

        {/* Layout controls panel */}
        <Panel position="top-right" className="layout-panel glass-panel">
          <div className="layout-panel__group">
            <button
              className={`layout-btn ${layoutMode === 'dagre' ? 'layout-btn--active' : ''}`}
              onClick={() => setLayoutMode('dagre')}
              title="Hierarchical layout"
            >
              ▤ Hierarchy
            </button>
            <button
              className={`layout-btn ${layoutMode === 'radial' ? 'layout-btn--active' : ''}`}
              onClick={() => setLayoutMode('radial')}
              title="Radial layout"
            >
              ◎ Radial
            </button>
          </div>

          {layoutMode === 'dagre' && (
            <div className="layout-panel__group">
              {(['TB', 'LR', 'BT', 'RL'] as LayoutDirection[]).map((dir) => (
                <button
                  key={dir}
                  className={`layout-btn layout-btn--small ${
                    layoutDirection === dir ? 'layout-btn--active' : ''
                  }`}
                  onClick={() => setLayoutDirection(dir)}
                >
                  {dir}
                </button>
              ))}
            </div>
          )}

          <button className="layout-btn layout-btn--refit" onClick={() => applyLayout()}>
            ↻ Re-layout
          </button>
        </Panel>

        {/* Node count indicator */}
        <Panel position="bottom-left" className="node-count-panel glass-panel">
          <span className="node-count">
            {flowNodes.length} nodes · {flowEdges.length} edges
          </span>
        </Panel>
      </ReactFlow>
    </div>
  );
}
