import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CodeEntity(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_entity.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    fully_qualified_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    visibility: Mapped[Optional[str]] = mapped_column(String(50), default="public", nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="code_entities")
    file: Mapped["File"] = relationship("File", back_populates="code_entities")
    parent: Mapped[Optional["CodeEntity"]] = relationship(
        "CodeEntity", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["CodeEntity"]] = relationship(
        "CodeEntity", back_populates="parent", cascade="all, delete-orphan"
    )
