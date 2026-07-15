import uuid
import logging
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.graph_sync import GraphSyncService
from app.services.graph_query import GraphQueryService
from app.core.exceptions import GraphSyncError

logger = logging.getLogger("app.api.v1.endpoints.graph")

router = APIRouter()

@router.post(
    "/{repository_id}/graph/sync",
    summary="Synchronize PostgreSQL metadata to Neo4j",
    description="Synchronizes files, entities, and dependency relationships from PostgreSQL to Neo4j.",
)
def sync_graph(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    try:
        result = GraphSyncService.sync_repository(db, repository_id)
        return result
    except GraphSyncError as e:
        logger.error(f"Graph synchronization failed: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during graph synchronization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{repository_id}/graph/summary",
    summary="Get repository graph summary statistics",
    description="Returns counts of nodes grouped by labels and edges grouped by relationship types.",
)
def get_graph_summary(repository_id: uuid.UUID):
    try:
        summary = GraphQueryService.get_repository_graph_summary(repository_id)
        return summary
    except Exception as e:
        logger.error(f"Failed to retrieve graph summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{repository_id}/graph/entity/{entity_id}/dependencies",
    summary="Get direct dependencies of a code entity",
    description="Returns direct inbound and outbound dependency edges for the specified entity.",
)
def get_entity_dependencies(entity_id: uuid.UUID):
    try:
        dependencies = GraphQueryService.get_entity_dependencies(entity_id)
        return dependencies
    except Exception as e:
        logger.error(f"Failed to retrieve entity dependencies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{repository_id}/graph/entity/{entity_id}/chain",
    summary="Get downstream dependency chain for an entity",
    description="Traverses downstream relationships up to a given depth (max 5).",
)
def get_dependency_chain(
    entity_id: uuid.UUID,
    depth: int = Query(default=3, ge=1, le=5, description="Traversal depth"),
):
    try:
        chain = GraphQueryService.get_dependency_chain(entity_id, depth)
        return chain
    except Exception as e:
        logger.error(f"Failed to retrieve dependency chain: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{repository_id}/graph/path",
    summary="Find shortest dependency path between two entities",
    description="Returns the shortest path (list of nodes and edges) between source and target entities.",
)
def find_shortest_path(
    source_id: uuid.UUID = Query(..., description="Source entity ID"),
    target_id: uuid.UUID = Query(..., description="Target entity ID"),
):
    try:
        path = GraphQueryService.find_shortest_path(source_id, target_id)
        return path
    except Exception as e:
        logger.error(f"Failed to compute shortest path: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{repository_id}/graph/cycles",
    summary="Detect circular dependencies",
    description="Finds and returns cycles of circular references in the repository's dependency graph.",
)
def detect_cycles(repository_id: uuid.UUID):
    try:
        cycles = GraphQueryService.detect_circular_dependencies(repository_id)
        return cycles
    except Exception as e:
        logger.error(f"Failed to detect circular dependencies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
