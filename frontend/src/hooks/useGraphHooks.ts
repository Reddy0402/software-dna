/**
 * Custom hooks for graph data loading, search, and statistics.
 */
import { useCallback, useEffect, useRef } from 'react';
import { useGraphStore } from '../store/graphStore';
import {
  fetchRepositories,
  fetchRepositoryGraph,
  fetchNodeNeighbors,
  searchEntities,
  fetchEntityDetail,
  fetchGraphStatistics,
} from '../api/graphApi';

// ----- useGraphData: loads initial graph and handles expansion -----

export function useGraphData() {
  const {
    selectedRepoId,
    setGraphData,
    addGraphData,
    setMeta,
    setLoading,
    setError,
    markNodeExpanded,
    expandedNodeIds,
    filters,
  } = useGraphStore();

  const loadGraph = useCallback(async () => {
    if (!selectedRepoId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRepositoryGraph(selectedRepoId, {
        limit: 200,
        offset: 0,
      });
      setGraphData(data.nodes, data.edges);
      setMeta(data.total_nodes, data.total_edges, data.has_more);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load graph';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedRepoId, setGraphData, setMeta, setLoading, setError]);

  const expandNode = useCallback(
    async (entityId: string) => {
      if (!selectedRepoId || expandedNodeIds.has(entityId)) return;
      try {
        const data = await fetchNodeNeighbors(selectedRepoId, entityId, {
          depth: 1,
          direction: 'both',
        });
        addGraphData(data.nodes, data.edges);
        markNodeExpanded(entityId);
      } catch (err: unknown) {
        console.error('Failed to expand node:', err);
      }
    },
    [selectedRepoId, expandedNodeIds, addGraphData, markNodeExpanded],
  );

  const loadEntityDetail = useCallback(
    async (entityId: string) => {
      if (!selectedRepoId) return null;
      try {
        return await fetchEntityDetail(selectedRepoId, entityId);
      } catch {
        return null;
      }
    },
    [selectedRepoId],
  );

  // Load graph when repo changes
  useEffect(() => {
    if (selectedRepoId) {
      loadGraph();
    }
  }, [selectedRepoId, loadGraph]);

  return { loadGraph, expandNode, loadEntityDetail };
}

// ----- useSearch: debounced entity search -----

export function useSearch() {
  const { selectedRepoId, setHighlightedNodeIds } = useGraphStore();
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const search = useCallback(
    async (query: string) => {
      if (!selectedRepoId || !query.trim()) {
        setHighlightedNodeIds(new Set());
        return [];
      }
      try {
        const results = await searchEntities(selectedRepoId, query, { limit: 20 });
        const ids = new Set(results.results.map((r) => r.entity.id));
        setHighlightedNodeIds(ids);
        return results.results;
      } catch {
        return [];
      }
    },
    [selectedRepoId, setHighlightedNodeIds],
  );

  const debouncedSearch = useCallback(
    (query: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => search(query), 300);
    },
    [search],
  );

  return { search, debouncedSearch };
}

// ----- useRepositories: load repository list -----

export function useRepositories() {
  const { setRepositories, setLoading, setError } = useGraphStore();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const repos = await fetchRepositories();
      setRepositories(repos);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load repositories';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [setRepositories, setLoading, setError]);

  useEffect(() => {
    load();
  }, [load]);

  return { reload: load };
}

// ----- useGraphStatistics: load graph statistics -----

export function useGraphStatistics() {
  const { selectedRepoId, setStatistics } = useGraphStore();

  const load = useCallback(async () => {
    if (!selectedRepoId) return;
    try {
      const stats = await fetchGraphStatistics(selectedRepoId);
      setStatistics(stats);
    } catch {
      console.error('Failed to load statistics');
    }
  }, [selectedRepoId, setStatistics]);

  useEffect(() => {
    if (selectedRepoId) load();
  }, [selectedRepoId, load]);

  return { reload: load };
}
