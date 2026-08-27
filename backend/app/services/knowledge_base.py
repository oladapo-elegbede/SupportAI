import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services.storage import FileStorageService, get_storage_service


class KBError(Exception):
    """Base exception for Knowledge Base operations."""
    pass


class KBNotFoundError(KBError):
    pass


class KBAlreadyExistsError(KBError):
    pass


class KBService:
    def __init__(self, db: AsyncSession, storage: Optional[FileStorageService] = None):
        self.db = db
        self.storage = storage or get_storage_service()

    async def create_kb(
        self, organization_id: uuid.UUID, data: KnowledgeBaseCreate
    ) -> KnowledgeBase:
        # Check unique name per organization
        existing = await self.db.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.organization_id == organization_id,
                KnowledgeBase.name == data.name,
            )
        )
        if existing:
            raise KBAlreadyExistsError(f"Knowledge Base named '{data.name}' already exists.")

        kb = KnowledgeBase(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
        )
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def get_kb_by_id(
        self, organization_id: uuid.UUID, kb_id: uuid.UUID
    ) -> KnowledgeBase:
        kb = await self.db.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.organization_id == organization_id,
            )
        )
        if not kb:
            raise KBNotFoundError("Knowledge Base not found.")
        return kb

    async def list_kbs(
        self, organization_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Tuple[KnowledgeBase, int]]:
        """Lists knowledge bases for tenant with document counts."""
        stmt = (
            select(KnowledgeBase, func.count(Document.id).label("doc_count"))
            .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
            .where(KnowledgeBase.organization_id == organization_id)
            .group_by(KnowledgeBase.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def update_kb(
        self,
        organization_id: uuid.UUID,
        kb_id: uuid.UUID,
        data: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        kb = await self.get_kb_by_id(organization_id, kb_id)

        if data.name and data.name != kb.name:
            existing = await self.db.scalar(
                select(KnowledgeBase).where(
                    KnowledgeBase.organization_id == organization_id,
                    KnowledgeBase.name == data.name,
                    KnowledgeBase.id != kb_id,
                )
            )
            if existing:
                raise KBAlreadyExistsError(f"Knowledge Base named '{data.name}' already exists.")
            kb.name = data.name

        if data.description is not None:
            kb.description = data.description

        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def delete_kb(
        self, organization_id: uuid.UUID, kb_id: uuid.UUID
    ) -> bool:
        kb = await self.get_kb_by_id(organization_id, kb_id)

        # Delete physical directory on disk: ./uploads/{org_id}/{kb_id}
        rel_dir = f"{organization_id}/{kb_id}"
        await self.storage.delete_directory(rel_dir)

        # Delete DB record (Cascades to documents table)
        await self.db.delete(kb)
        await self.db.commit()
        return True
