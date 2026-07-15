import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, Integer, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Repository(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    clone_status: Mapped[str] = mapped_column(String(50), default="pending")
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    default_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parser_status: Mapped[str] = mapped_column(String(50), default="pending")
    graph_status: Mapped[str] = mapped_column(String(50), default="pending")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata fields
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latest_commit_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    total_files: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    files: Mapped[list["File"]] = relationship(
        "File", back_populates="repository", cascade="all, delete-orphan"
    )
    code_entities: Mapped[list["CodeEntity"]] = relationship(
        "CodeEntity", back_populates="repository", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list["Dependency"]] = relationship(
        "Dependency", back_populates="repository", cascade="all, delete-orphan"
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
