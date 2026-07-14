import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.file import File
from app.services.parser import ParserService

router = APIRouter()


@router.post(
    "/{file_id}/parse",
    status_code=status.HTTP_200_OK,
    summary="Parse a scanned file into an AST",
    description="Loads a file metadata record from PostgreSQL, reads its source content, parses it using Tree-sitter, and returns a circular-safe flat AST representation."
)
def parse_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> dict:
    # 1. Fetch file record from DB
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File record with ID {file_id} not found"
        )
        
    # 2. Check if absolute path exists on disk
    if not file_record.absolute_path or not os.path.exists(file_record.absolute_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source file does not exist on disk at: '{file_record.absolute_path}'"
        )
        
    # 3. Parse file from disk
    parsed_rep = ParserService.parse_file_path(
        absolute_path=file_record.absolute_path,
        relative_path=file_record.relative_path,
        language=file_record.language
    )
    
    if parsed_rep.status == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse source file due to parser configuration or file read error."
        )
        
    return parsed_rep.to_dict()
