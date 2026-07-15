import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.services.dependency_extractor import DependencyExtractionService
from app.schemas.dependency import DependencyResponse, DependencyStats
from app.models.dependency import Dependency
from app.core.exceptions import DependencyExtractionError

logger = logging.getLogger("app.api.v1.endpoints.dependencies")

router = APIRouter()


@router.post(
    "/{repository_id}/dependencies/extract",
    response_model=DependencyStats,
    summary="Extract dependencies for a repository",
    description="Runs the full dependency extraction pipeline: retrieves metadata, "
                "analyzes relationships, validates, and persists results.",
)
def extract_dependencies(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Trigger the dependency extraction pipeline for the given repository."""
    try:
        stats = DependencyExtractionService.extract_dependencies(
            db=db, repository_id=repository_id
        )
        return DependencyStats(**stats)
    except DependencyExtractionError as e:
        logger.error(f"Dependency extraction failed: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during dependency extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{repository_id}/dependencies",
    response_model=List[DependencyResponse],
    summary="List extracted dependencies",
    description="Returns paginated dependencies for a repository, "
                "optionally filtered by relationship type.",
)
def list_dependencies(
    repository_id: uuid.UUID,
    relationship_type: str = Query(default=None, description="Filter by relationship type"),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=100, ge=1, le=500, description="Pagination limit"),
    db: Session = Depends(get_db),
):
    """List extracted dependencies with optional filtering and pagination."""
    query = db.query(Dependency).filter(
        Dependency.repository_id == repository_id
    )

    if relationship_type:
        query = query.filter(
            Dependency.relationship_type == relationship_type
        )

    dependencies = query.offset(skip).limit(limit).all()
    return dependencies
