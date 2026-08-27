import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Integer, DateTime, UUID, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.knowledge_base import KnowledgeBase


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint("file_type IN ('pdf', 'txt')", name="ck_documents_file_type"),
        CheckConstraint(
            "ingestion_status IN ('uploaded', 'pending', 'processing', 'completed', 'failed')",
            name="ck_documents_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    ingestion_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
    )
    ingestion_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="documents",
    )
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="documents",
    )
