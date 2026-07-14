import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    absolute_path: str
    relative_path: str
    filename: str
    extension: str
    language: str
    depth: int
    size_bytes: int
    last_modified: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanSummaryResponse(BaseModel):
    repository_id: uuid.UUID
    total_files_scanned: int
    supported_files_found: int
    language_distribution: dict[str, int]
