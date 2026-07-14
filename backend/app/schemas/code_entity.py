import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class CodeEntityResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    file_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    entity_type: str
    name: str
    fully_qualified_name: str
    start_line: int
    end_line: int
    visibility: Optional[str] = "public"
    language: str
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
