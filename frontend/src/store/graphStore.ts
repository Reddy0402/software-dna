/**
 * Zustand store for graph explorer state management.
 */
import { create } from 'zustand';
import type {
  GraphNode,
  GraphEdge,
  RepositorySummary,
  EntityDetail,
  GraphStatistics,
  FilterState,
  ViewMode,
  EntityType,
  RelationshipType,
} from '../types/graph';
import { NODE_TYPE_OPTIONS, RELATIONSHIP_TYPE_OPTIONS } from '../types/graph';

interface GraphState {
  // View
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  // Repositories
  repositories: RepositorySummary[];
  setRepositories: (repos: RepositorySummary[]) => void;
  selectedRepoId: string | null;
  setSelectedRepoId: (id: string | null) => void;

  // Graph data
  nodes: GraphNode[];
  edges: GraphEdge[];
  setGraphData: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  addGraphData: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  clearGraph: () => void;
  totalNodes: number;
  totalEdges: number;
  hasMore: boolean;
  setMeta: (total_nodes: number, total_edges: number, has_more: boolean) => void;

  // Selection
  selectedNodeId: string | null;
  setSelectedNodeId: (id: string | null) => void;
  selectedEntityDetail: EntityDetail | null;
  setSelectedEntityDetail: (detail: EntityDetail | null) => void;

  // Filters
  filters: FilterState;
  setNodeTypeFilter: (types: EntityType[]) => void;
  setRelTypeFilter: (types: RelationshipType[]) => void;
  resetFilters: () => void;

  // Search
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  highlightedNodeIds: Set<string>;
  setHighlightedNodeIds: (ids: Set<string>) => void;

  // Statistics
  statistics: GraphStatistics | null;
  setStatistics: (stats: GraphStatistics | null) => void;

  // UI panels
  isDetailPanelOpen: boolean;
  setDetailPanelOpen: (open: boolean) => void;
  isFilterPanelOpen: boolean;
  setFilterPanelOpen: (open: boolean) => void;
  isStatsPanelOpen: boolean;
  setStatsPanelOpen: (open: boolean) => void;

  // Loading
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;

  // Expanded nodes tracking (for lazy loading)
  expandedNodeIds: Set<string>;
  markNodeExpanded: (id: string) => void;
}

export const useGraphStore = create<GraphState>((set, get) => ({
  // View
  viewMode: 'dashboard',
  setViewMode: (mode) => set({ viewMode: mode }),

  // Repositories
  repositories: [],
  setRepositories: (repos) => set({ repositories: repos }),
  selectedRepoId: null,
  setSelectedRepoId: (id) => set({ selectedRepoId: id }),

  // Graph data
  nodes: [],
  edges: [],
  setGraphData: (nodes, edges) => set({ nodes, edges }),
  addGraphData: (newNodes, newEdges) => {
    const { nodes, edges } = get();
    const existingNodeIds = new Set(nodes.map((n) => n.id));
    const existingEdgeIds = new Set(edges.map((e) => e.id));
    const uniqueNewNodes = newNodes.filter((n) => !existingNodeIds.has(n.id));
    const uniqueNewEdges = newEdges.filter((e) => !existingEdgeIds.has(e.id));
    set({
      nodes: [...nodes, ...uniqueNewNodes],
      edges: [...edges, ...uniqueNewEdges],
    });
  },
  clearGraph: () =>
    set({
      nodes: [],
      edges: [],
      selectedNodeId: null,
      selectedEntityDetail: null,
      expandedNodeIds: new Set(),
      highlightedNodeIds: new Set(),
      totalNodes: 0,
      totalEdges: 0,
      hasMore: false,
    }),
  totalNodes: 0,
  totalEdges: 0,
  hasMore: false,
  setMeta: (total_nodes, total_edges, has_more) =>
    set({ totalNodes: total_nodes, totalEdges: total_edges, hasMore: has_more }),

  // Selection
  selectedNodeId: null,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  selectedEntityDetail: null,
  setSelectedEntityDetail: (detail) => set({ selectedEntityDetail: detail }),

  // Filters
  filters: {
    nodeTypes: [...NODE_TYPE_OPTIONS],
    relationshipTypes: [...RELATIONSHIP_TYPE_OPTIONS],
  },
  setNodeTypeFilter: (types) =>
    set((s) => ({ filters: { ...s.filters, nodeTypes: types } })),
  setRelTypeFilter: (types) =>
    set((s) => ({ filters: { ...s.filters, relationshipTypes: types } })),
  resetFilters: () =>
    set({
      filters: {
        nodeTypes: [...NODE_TYPE_OPTIONS],
        relationshipTypes: [...RELATIONSHIP_TYPE_OPTIONS],
      },
    }),

  // Search
  searchQuery: '',
  setSearchQuery: (q) => set({ searchQuery: q }),
  highlightedNodeIds: new Set(),
  setHighlightedNodeIds: (ids) => set({ highlightedNodeIds: ids }),

  // Statistics
  statistics: null,
  setStatistics: (stats) => set({ statistics: stats }),

  // UI panels
  isDetailPanelOpen: false,
  setDetailPanelOpen: (open) => set({ isDetailPanelOpen: open }),
  isFilterPanelOpen: false,
  setFilterPanelOpen: (open) => set({ isFilterPanelOpen: open }),
  isStatsPanelOpen: false,
  setStatsPanelOpen: (open) => set({ isStatsPanelOpen: open }),

  // Loading
  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),
  error: null,
  setError: (error) => set({ error }),

  // Expanded nodes
  expandedNodeIds: new Set(),
  markNodeExpanded: (id) =>
    set((s) => {
      const next = new Set(s.expandedNodeIds);
      next.add(id);
      return { expandedNodeIds: next };
    }),
}));
