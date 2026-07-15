import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class DependencyResponse(BaseModel):
    """API serialization model for a single dependency relationship."""
    id: uuid.UUID
    repository_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: Optional[uuid.UUID] = None
    relationship_type: str
    confidence: float
    source_file: str
    line_number: int
    target_fqn: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DependencyStats(BaseModel):
    """Summary statistics returned after a dependency extraction run."""
    repository_id: uuid.UUID
    total_dependencies: int
    by_relationship_type: Dict[str, int]
    avg_confidence: float
    unresolved_count: int
