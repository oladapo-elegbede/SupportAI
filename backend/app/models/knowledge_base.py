import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, DateTime, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.document import Document


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_kb_org_name"),
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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
        back_populates="knowledge_bases",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
