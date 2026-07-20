"""
Graph Explorer API Endpoints
============================
Dedicated REST API for the interactive graph visualization frontend.
Mounted at /api/v1/graph.
"""
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.repository import Repository
from app.services.graph_query import GraphQueryService
from app.schemas.graph import (
    GraphData,
    NeighborData,
    SearchResults,
    SearchResultItem,
    EntityDetail,
    HierarchyData,
    PathData,
    GraphStatistics,
    RepositorySummary,
)
from app.core.exceptions import GraphQueryError

logger = logging.getLogger("app.api.v1.endpoints.graph_explorer")

router = APIRouter()


# --------------------------------------------------------------------------
# Repository listing
# --------------------------------------------------------------------------

@router.get(
    "/repositories",
    response_model=List[RepositorySummary],
    summary="List all repositories with graph status",
    description=(
        "Returns every repository with its clone/parse/graph status and "
        "summary counts suitable for the dashboard view."
    ),
)
def list_repositories_with_graph_status(
    db: Session = Depends(get_db),
):
    """List all repositories enriched with graph summary data."""
    try:
        repos = db.query(Repository).order_by(Repository.created_at.desc()).all()
        results = []
        for repo in repos:
            summary_data = {
                "id": repo.id,
                "name": repo.name,
                "url": repo.url,
                "owner": repo.owner,
                "clone_status": repo.clone_status,
                "parser_status": repo.parser_status,
                "graph_status": repo.graph_status,
                "total_files": repo.total_files,
                "total_nodes": 0,
                "total_edges": 0,
                "nodes_by_label": {},
                "edges_by_type": {},
            }
            # Attempt to enrich with Neo4j counts if graph is synced
            if repo.graph_status == "completed":
                try:
                    graph_summary = GraphQueryService.get_repository_graph_summary(repo.id)
                    summary_data["total_nodes"] = graph_summary.get("total_nodes", 0)
                    summary_data["total_edges"] = graph_summary.get("total_edges", 0)
                    summary_data["nodes_by_label"] = graph_summary.get("nodes_by_label", {})
                    summary_data["edges_by_type"] = graph_summary.get("edges_by_type", {})
                except Exception:
                    logger.warning(f"Could not fetch graph summary for repo {repo.id}")
            results.append(RepositorySummary(**summary_data))
        return results
    except Exception as e:
        logger.error(f"Failed to list repositories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Full repository graph (paginated)
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/graph",
    response_model=GraphData,
    summary="Get full repository graph data",
    description=(
        "Returns paginated graph nodes and edges for visualization. "
        "Supports filtering by node types and relationship types."
    ),
)
def get_repository_graph(
    repository_id: uuid.UUID,
    node_types: Optional[str] = Query(
        default=None,
        description="Comma-separated node types to include (e.g. Class,Method,Function)",
    ),
    relationship_types: Optional[str] = Query(
        default=None,
        description="Comma-separated relationship types (e.g. CALLS,IMPORTS)",
    ),
    limit: int = Query(default=200, ge=1, le=500, description="Max entities to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
):
    """Retrieve the repository graph with optional filtering and pagination."""
    try:
        nt = [t.strip() for t in node_types.split(",") if t.strip()] if node_types else None
        rt = [t.strip() for t in relationship_types.split(",") if t.strip()] if relationship_types else None

        data = GraphQueryService.get_repository_graph(
            repository_id=repository_id,
            node_types=nt,
            relationship_types=rt,
            limit=limit,
            offset=offset,
        )
        return GraphData(**data)
    except Exception as e:
        logger.error(f"Failed to retrieve repository graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Neighborhood expansion
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/graph/neighbors/{entity_id}",
    response_model=NeighborData,
    summary="Expand node neighborhood",
    description="Returns neighboring nodes and edges for lazy graph expansion.",
)
def get_node_neighbors(
    repository_id: uuid.UUID,
    entity_id: uuid.UUID,
    relationship_types: Optional[str] = Query(
        default=None,
        description="Comma-separated relationship types to follow",
    ),
    direction: str = Query(
        default="both",
        regex="^(in|out|both)$",
        description="Edge direction: in, out, or both",
    ),
    depth: int = Query(default=1, ge=1, le=3, description="Expansion depth"),
):
    """Expand the neighborhood of a single node."""
    try:
        rt = [t.strip() for t in relationship_types.split(",") if t.strip()] if relationship_types else None
        data = GraphQueryService.get_node_neighbors(
            entity_id=entity_id,
            relationship_types=rt,
            direction=direction,
            depth=depth,
        )
        return NeighborData(**data)
    except Exception as e:
        logger.error(f"Failed to get node neighbors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/graph/search",
    response_model=SearchResults,
    summary="Search entities by name or FQN",
    description=(
        "Case-insensitive search across entity names and fully qualified names. "
        "Results are ranked by match quality."
    ),
)
def search_entities(
    repository_id: uuid.UUID,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    entity_types: Optional[str] = Query(
        default=None,
        description="Comma-separated entity types to filter (e.g. Class,Method)",
    ),
    limit: int = Query(default=20, ge=1, le=50, description="Max results"),
):
    """Search entities within a repository by name or FQN."""
    try:
        et = [t.strip() for t in entity_types.split(",") if t.strip()] if entity_types else None
        results = GraphQueryService.search_entities(
            repository_id=repository_id,
            query_text=q,
            entity_types=et,
            limit=limit,
        )
        items = [SearchResultItem(**r) for r in results]
        return SearchResults(query=q, results=items, total=len(items))
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Entity detail
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/graph/entity/{entity_id}",
    response_model=EntityDetail,
    summary="Get detailed entity metadata",
    description=(
        "Returns full entity detail including file context, "
        "incoming and outgoing relationships."
    ),
)
def get_entity_detail(
    repository_id: uuid.UUID,
    entity_id: uuid.UUID,
):
    """Retrieve comprehensive detail for a single entity."""
    try:
        detail = GraphQueryService.get_entity_detail(entity_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return EntityDetail(**detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Repository hierarchy
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/graph/hierarchy",
    response_model=HierarchyData,
    summary="Get file-entity hierarchy",
    description="Returns a tree structure of Repository → Files → Entities.",
)
def get_repository_hierarchy(repository_id: uuid.UUID):
    """Retrieve the file/entity tree structure."""
    try:
        data = GraphQueryService.get_repository_hierarchy(repository_id)
        return HierarchyData(**data)
    except Exception as e:
        logger.error(f"Failed to get hierarchy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Dependency path
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/graph/path",
    response_model=PathData,
    summary="Find dependency path between two entities",
    description="Returns the shortest dependency path with configurable max depth.",
)
def find_dependency_path(
    repository_id: uuid.UUID,
    source_id: uuid.UUID = Query(..., description="Source entity UUID"),
    target_id: uuid.UUID = Query(..., description="Target entity UUID"),
    max_depth: int = Query(default=10, ge=1, le=15, description="Maximum path depth"),
):
    """Find the shortest dependency path between two entities."""
    try:
        data = GraphQueryService.get_dependency_path(
            source_id=source_id,
            target_id=target_id,
            max_depth=max_depth,
        )
        return PathData(**data)
    except Exception as e:
        logger.error(f"Failed to find path: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Graph statistics
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/graph/statistics",
    response_model=GraphStatistics,
    summary="Get comprehensive graph statistics",
    description=(
        "Returns node/edge counts, density, average degree, "
        "language distribution, and complexity metrics."
    ),
)
def get_graph_statistics(repository_id: uuid.UUID):
    """Retrieve comprehensive graph analytics."""
    try:
        data = GraphQueryService.get_graph_statistics(repository_id)
        return GraphStatistics(**data)
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
