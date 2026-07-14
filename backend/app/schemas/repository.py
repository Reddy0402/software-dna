import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, ConfigDict
from app.utils.git import GitUtility


class RepositoryCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v_clean = v.strip()
        if not GitUtility.validate_github_url(v_clean):
            raise ValueError(
                "URL must be a valid GitHub repository link (e.g., https://github.com/owner/repo)"
            )
        return v_clean


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    url: str
    local_path: Optional[str] = None
    clone_status: str
    owner: Optional[str] = None
    default_branch: Optional[str] = None
    parser_status: str
    graph_status: str
    last_error: Optional[str] = None

    size_bytes: Optional[int] = None
    latest_commit_hash: Optional[str] = None
    total_files: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
