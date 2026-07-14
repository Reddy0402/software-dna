import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.code_entity import CodeEntityResponse
from app.services.extractor import ExtractionService
from app.core.exceptions import RepositoryImportError

router = APIRouter()


@router.post(
    "/{file_id}/extract",
    response_model=List[CodeEntityResponse],
    status_code=status.HTTP_200_OK,
    summary="Extract programming constructs from a file",
    description="Loads a file, parses its contents into an AST, runs language-specific visitors, and persists code entities in PostgreSQL."
)
def extract_metadata(
    file_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> List[CodeEntityResponse]:
    try:
        entities = ExtractionService.extract_metadata(db, file_id)
        return entities
    except RepositoryImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extraction failed: {str(e)}"
        )
