import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Dependency(Base):
    """
    Represents a single dependency relationship between two code entities.
    Each row is a directed edge: source_entity --[relationship_type]--> target_entity.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_entity.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_entity.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    source_file: Mapped[str] = mapped_column(
        String(1024), nullable=False
    )
    line_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    target_fqn: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    meta_data: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="dependencies"
    )
    source_entity: Mapped["CodeEntity"] = relationship(
        "CodeEntity", foreign_keys=[source_entity_id], back_populates="source_dependencies"
    )
    target_entity: Mapped[Optional["CodeEntity"]] = relationship(
        "CodeEntity", foreign_keys=[target_entity_id], back_populates="target_dependencies"
    )
