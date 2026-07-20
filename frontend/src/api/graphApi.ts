/**
 * API client for the Graph Explorer backend.
 * All calls target /api/v1/graph/* endpoints.
 */
import axios from 'axios';
import type {
  RepositorySummary,
  GraphData,
  NeighborData,
  SearchResults,
  EntityDetail,
  HierarchyData,
  PathData,
  GraphStatistics,
} from '../types/graph';

const api = axios.create({
  baseURL: '/api/v1/graph',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ---- Repositories ----

export async function fetchRepositories(): Promise<RepositorySummary[]> {
  const { data } = await api.get<RepositorySummary[]>('/repositories');
  return data;
}

// ---- Full Graph ----

export async function fetchRepositoryGraph(
  repoId: string,
  params?: {
    node_types?: string;
    relationship_types?: string;
    limit?: number;
    offset?: number;
  },
): Promise<GraphData> {
  const { data } = await api.get<GraphData>(`/repositories/${repoId}/graph`, { params });
  return data;
}

// ---- Neighbors ----

export async function fetchNodeNeighbors(
  repoId: string,
  entityId: string,
  params?: {
    relationship_types?: string;
    direction?: 'in' | 'out' | 'both';
    depth?: number;
  },
): Promise<NeighborData> {
  const { data } = await api.get<NeighborData>(
    `/repositories/${repoId}/graph/neighbors/${entityId}`,
    { params },
  );
  return data;
}

// ---- Search ----

export async function searchEntities(
  repoId: string,
  query: string,
  params?: {
    entity_types?: string;
    limit?: number;
  },
): Promise<SearchResults> {
  const { data } = await api.get<SearchResults>(
    `/repositories/${repoId}/graph/search`,
    { params: { q: query, ...params } },
  );
  return data;
}

// ---- Entity Detail ----

export async function fetchEntityDetail(
  repoId: string,
  entityId: string,
): Promise<EntityDetail> {
  const { data } = await api.get<EntityDetail>(
    `/repositories/${repoId}/graph/entity/${entityId}`,
  );
  return data;
}

// ---- Hierarchy ----

export async function fetchHierarchy(repoId: string): Promise<HierarchyData> {
  const { data } = await api.get<HierarchyData>(
    `/repositories/${repoId}/graph/hierarchy`,
  );
  return data;
}

// ---- Path ----

export async function fetchDependencyPath(
  repoId: string,
  sourceId: string,
  targetId: string,
  maxDepth = 10,
): Promise<PathData> {
  const { data } = await api.get<PathData>(
    `/repositories/${repoId}/graph/path`,
    { params: { source_id: sourceId, target_id: targetId, max_depth: maxDepth } },
  );
  return data;
}

// ---- Statistics ----

export async function fetchGraphStatistics(repoId: string): Promise<GraphStatistics> {
  const { data } = await api.get<GraphStatistics>(
    `/repositories/${repoId}/graph/statistics`,
  );
  return data;
}
