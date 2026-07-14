from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.services.repository import RepositoryService
from app.core.exceptions import RepositoryImportError

router = APIRouter()


@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import a GitHub repository",
    description=(
        "Accepts a GitHub repository URL, validates it, clones the repository "
        "locally, extracts repository metadata, and saves everything in the database."
    )
)
def import_repository(
    payload: RepositoryCreate,
    db: Session = Depends(get_db)
) -> RepositoryResponse:
    try:
        # Create database record in 'pending' status
        db_record = RepositoryService.create_pending_record(db, payload.url)
    except RepositoryImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {str(e)}"
        )

    try:
        # Execute checkout, clone, and metadata collection
        updated_record = RepositoryService.import_repository(db, db_record.id)
        return updated_record
    except RepositoryImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository import failed: {str(e)}"
        )
