import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.file import ScanSummaryResponse
from app.services.scanner import ScannerService
from app.core.exceptions import RepositoryImportError

router = APIRouter()


@router.post(
    "/{repository_id}/scan",
    response_model=ScanSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan an imported repository for source files",
    description="Recursively scans local workspace directories, builds a manifest of supported source files, and records them in PostgreSQL."
)
def scan_repository(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> ScanSummaryResponse:
    try:
        summary = ScannerService.scan_repository(db, repository_id)
        return summary
    except RepositoryImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scan failed: {str(e)}"
        )
