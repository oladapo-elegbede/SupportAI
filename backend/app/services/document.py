import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.services.storage import FileStorageService, get_storage_service
from app.core.queue import enqueue_ingestion_job


MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB Limit


class DocumentError(Exception):
    """Base exception for document operations."""
    pass


class DocumentNotFoundError(DocumentError):
    pass


class FileValidationError(DocumentError):
    pass


class DocumentService:
    def __init__(self, db: AsyncSession, storage: Optional[FileStorageService] = None):
        self.db = db
        self.storage = storage or get_storage_service()

    def validate_file(self, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """Validates file extension, size, and magic bytes. Returns (sanitized_filename, file_type)."""
        if len(file_bytes) == 0:
            raise FileValidationError("Uploaded file is empty.")

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise FileValidationError("File size exceeds limit of 20MB.")

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ["pdf", "txt"]:
            raise FileValidationError("Only PDF (.pdf) and Plain Text (.txt) files are allowed.")

        if ext == "pdf":
            if not file_bytes.startswith(b"%PDF-"):
                raise FileValidationError("Invalid PDF file format (failed magic byte check).")
        elif ext == "txt":
            try:
                file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise FileValidationError("TXT file must be valid UTF-8 encoded text.")

        clean_name = filename.replace("\\", "/").split("/")[-1]
        return clean_name, ext

    async def upload_document(
        self,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        filename: str,
        file_bytes: bytes,
    ) -> Document:
        # 1. Verify Knowledge Base exists & belongs to tenant
        kb = await self.db.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.organization_id == organization_id,
            )
        )
        if not kb:
            raise DocumentError("Knowledge Base not found.")

        # 2. Validate File
        clean_filename, file_type = self.validate_file(filename, file_bytes)

        # 3. Create Document DB record with status = 'pending'
        doc_id = uuid.uuid4()
        rel_file_path = f"{organization_id}/{knowledge_base_id}/{doc_id}.{file_type}"

        doc = Document(
            id=doc_id,
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            filename=clean_filename,
            file_path=rel_file_path,
            file_type=file_type,
            file_size_bytes=len(file_bytes),
            ingestion_status="pending",
            ingestion_version=1,
        )

        # 4. Save file to disk
        await self.storage.save_file(file_bytes, rel_file_path)

        # 5. Commit DB record
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        # 6. Enqueue background ingestion job in Redis
        await enqueue_ingestion_job(doc.id, organization_id)

        return doc

    async def reingest_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        """Re-triggers document ingestion pipeline (e.g. after failure or tuning)."""
        doc = await self.get_document_by_id(organization_id, document_id)

        doc.ingestion_status = "pending"
        doc.ingestion_version += 1
        doc.error_message = None
        await self.db.commit()
        await self.db.refresh(doc)

        # Enqueue job in Redis
        await enqueue_ingestion_job(doc.id, organization_id)

        return doc

    async def get_document_by_id(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        doc = await self.db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.organization_id == organization_id,
            )
        )
        if not doc:
            raise DocumentNotFoundError("Document not found.")
        return doc

    async def list_documents(
        self,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        stmt = (
            select(Document)
            .where(
                Document.organization_id == organization_id,
                Document.knowledge_base_id == knowledge_base_id,
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> bool:
        doc = await self.get_document_by_id(organization_id, document_id)

        await self.storage.delete_file(doc.file_path)
        await self.db.delete(doc)
        await self.db.commit()
        return True
