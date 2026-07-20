/**
 * TypeScript interfaces matching the backend Graph Explorer API schemas.
 */

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  entity_type: EntityType;
  fully_qualified_name: string;
  language: string;
  file_path: string;
  start_line: number | null;
  end_line: number | null;
  visibility: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: RelationshipType;
  confidence: number;
  source_file: string;
  line_number: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  has_more: boolean;
}

export interface NeighborData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SearchResultItem {
  entity: GraphNode;
  match_field: string;
}

export interface SearchResults {
  query: string;
  results: SearchResultItem[];
  total: number;
}

export interface FileInfo {
  id: string;
  relative_path: string;
  filename: string;
  language: string;
  size_bytes: number;
}

export interface RelationshipDetail {
  relationship_type: string;
  source?: GraphNode;
  target?: GraphNode;
}

export interface EntityDetail {
  entity: GraphNode;
  file: FileInfo | null;
  outgoing_relationships: RelationshipDetail[];
  incoming_relationships: RelationshipDetail[];
  outgoing_count: number;
  incoming_count: number;
}

export interface HierarchyFile {
  file: GraphNode;
  entities: GraphNode[];
  entity_count: number;
}

export interface HierarchyData {
  repository: { id: string; name: string; url: string } | null;
  children: HierarchyFile[];
  total_files: number;
  total_entities: number;
}

export interface PathData {
  path_found: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
  length: number;
}

export interface ComplexityMetrics {
  files: number;
  entities: number;
  relationships: number;
  types_used: number;
  relationship_types_used: number;
}

export interface GraphStatistics {
  repository_id: string;
  total_nodes: number;
  total_files: number;
  total_entities: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
  density: number;
  avg_degree: number;
  languages: Record<string, number>;
  complexity: ComplexityMetrics;
}

export interface RepositorySummary {
  id: string;
  name: string;
  url: string;
  owner: string | null;
  clone_status: string;
  parser_status: string;
  graph_status: string;
  total_files: number | null;
  total_nodes: number;
  total_edges: number;
  nodes_by_label: Record<string, number>;
  edges_by_type: Record<string, number>;
}

// Enums
export type EntityType =
  | 'class'
  | 'interface'
  | 'function'
  | 'method'
  | 'import'
  | 'module'
  | 'file'
  | 'repository'
  | 'external'
  | 'struct'
  | 'namespace'
  | 'constructor'
  | 'unknown';

export type RelationshipType =
  | 'IMPORTS'
  | 'CALLS'
  | 'EXTENDS'
  | 'IMPLEMENTS'
  | 'USES'
  | 'DEPENDS_ON'
  | 'REFERENCES'
  | 'CONTAINS'
  | 'DEFINES'
  | 'DEFINED_IN'
  | 'BELONGS_TO';

export const NODE_TYPE_OPTIONS: EntityType[] = [
  'file', 'class', 'interface', 'function', 'method', 'import', 'module', 'external',
];

export const RELATIONSHIP_TYPE_OPTIONS: RelationshipType[] = [
  'IMPORTS', 'CALLS', 'EXTENDS', 'IMPLEMENTS', 'USES', 'DEPENDS_ON',
  'REFERENCES', 'CONTAINS', 'DEFINES',
];

// View state types
export type ViewMode = 'dashboard' | 'explorer' | 'analytics';

export interface FilterState {
  nodeTypes: EntityType[];
  relationshipTypes: RelationshipType[];
}
