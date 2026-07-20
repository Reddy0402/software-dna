"""
Pydantic response schemas for the Graph Explorer API.
These models define the contract between backend and frontend for all
graph visualization data.
"""
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class GraphNode(BaseModel):
    """A single node in the visualization graph."""
    id: str
    label: str
    name: str
    entity_type: str
    fully_qualified_name: str = ""
    language: str = ""
    file_path: str = ""
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    visibility: str = ""
    metadata: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    """A single edge (relationship) in the visualization graph."""
    id: str
    source: str
    target: str
    relationship_type: str
    confidence: float = 1.0
    source_file: str = ""
    line_number: int = 0


class GraphData(BaseModel):
    """Paginated graph data containing nodes and edges."""
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    total_nodes: int = 0
    total_edges: int = 0
    has_more: bool = False


class NeighborData(BaseModel):
    """Neighborhood expansion result for a single node."""
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []


class SearchResultItem(BaseModel):
    """A single search result with the matched entity and match info."""
    entity: GraphNode
    match_field: str = "name_contains"


class SearchResults(BaseModel):
    """Collection of search results."""
    query: str
    results: List[SearchResultItem] = []
    total: int = 0


class RelationshipDetail(BaseModel):
    """A relationship with its connected entity detail."""
    relationship_type: str
    source: Optional[GraphNode] = None
    target: Optional[GraphNode] = None


class FileInfo(BaseModel):
    """File context for an entity."""
    id: str
    relative_path: str = ""
    filename: str = ""
    language: str = ""
    size_bytes: int = 0


class EntityDetail(BaseModel):
    """Full detail for a single entity including relationships."""
    entity: GraphNode
    file: Optional[FileInfo] = None
    outgoing_relationships: List[RelationshipDetail] = []
    incoming_relationships: List[RelationshipDetail] = []
    outgoing_count: int = 0
    incoming_count: int = 0


class HierarchyFile(BaseModel):
    """A file in the hierarchy tree with its child entities."""
    file: GraphNode
    entities: List[GraphNode] = []
    entity_count: int = 0


class RepositoryInfo(BaseModel):
    """Minimal repository info for hierarchy."""
    id: str
    name: str
    url: str = ""


class HierarchyData(BaseModel):
    """Tree-structured hierarchy: Repository -> Files -> Entities."""
    repository: Optional[RepositoryInfo] = None
    children: List[HierarchyFile] = []
    total_files: int = 0
    total_entities: int = 0


class PathData(BaseModel):
    """Shortest path result between two entities."""
    path_found: bool = False
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    length: int = 0


class ComplexityMetrics(BaseModel):
    """Complexity metrics for the graph."""
    files: int = 0
    entities: int = 0
    relationships: int = 0
    types_used: int = 0
    relationship_types_used: int = 0


class GraphStatistics(BaseModel):
    """Comprehensive graph analytics for a repository."""
    repository_id: str
    total_nodes: int = 0
    total_files: int = 0
    total_entities: int = 0
    total_edges: int = 0
    nodes_by_type: Dict[str, int] = {}
    edges_by_type: Dict[str, int] = {}
    density: float = 0.0
    avg_degree: float = 0.0
    languages: Dict[str, int] = {}
    complexity: ComplexityMetrics = ComplexityMetrics()


class RepositorySummary(BaseModel):
    """Repository with graph status and summary counts for the dashboard."""
    id: uuid.UUID
    name: str
    url: str
    owner: Optional[str] = None
    clone_status: str = "pending"
    parser_status: str = "pending"
    graph_status: str = "pending"
    total_files: Optional[int] = None
    total_nodes: int = 0
    total_edges: int = 0
    nodes_by_label: Dict[str, int] = {}
    edges_by_type: Dict[str, int] = {}

    model_config = ConfigDict(from_attributes=True)
