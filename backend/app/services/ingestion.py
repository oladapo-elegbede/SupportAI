import uuid
from datetime import datetime, timezone
import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.storage import FileStorageService, get_storage_service
from app.services.extractor import TextExtractorService, ExtractionError
from app.services.chunker import TextChunkerService
from app.services.embedding import EmbeddingService, get_embedding_service

logger = structlog.get_logger("supportai.ingestion")


class IngestionError(Exception):
    """Base exception for ingestion pipeline failures."""
    pass


class IngestionService:
    """Orchestrates the document ingestion pipeline: Read -> Extract -> Chunk -> Embed -> Store."""

    def __init__(
        self,
        db: AsyncSession,
        storage: FileStorageService | None = None,
        extractor: TextExtractorService | None = None,
        chunker: TextChunkerService | None = None,
        embedding: EmbeddingService | None = None,
    ):
        self.db = db
        self.storage = storage or get_storage_service()
        self.extractor = extractor or TextExtractorService()
        self.chunker = chunker or TextChunkerService(chunk_size=500, chunk_overlap=50)
        self.embedding = embedding or get_embedding_service()

    async def process_document(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        """
        Executes the full ingestion state machine asynchronously with idempotent clean-slate retries.
        """
        # 1. Fetch Document record
        doc = await self.db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.organization_id == organization_id,
            )
        )
        if not doc:
            logger.error("ingestion_doc_not_found", document_id=str(document_id))
            return False

        logger.info(
            "ingestion_started",
            document_id=str(document_id),
            filename=doc.filename,
            file_type=doc.file_type,
        )

        try:
            # 2. Update status -> 'processing'
            doc.ingestion_status = "processing"
            doc.error_message = None
            await self.db.commit()

            # 3. IDEMPOTENT RETRY CLEANUP: Purge any pre-existing chunks for this document
            await self.db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            await self.db.commit()

            # 4. Read raw file bytes from storage
            file_bytes = await self.storage.get_file(doc.file_path)

            # 5. Extract page-numbered text
            pages_text = await self.extractor.extract_text(file_bytes, doc.file_type)

            # 6. Clean and chunk text recursively
            chunks_data = self.chunker.chunk_document_pages(pages_text)
            if not chunks_data:
                raise IngestionError("Document contained no readable text after chunking.")

            # 7. Generate batch embeddings via Ollama nomic-embed-text (768 dims)
            chunk_texts = [c.text for c in chunks_data]
            embeddings = await self.embedding.embed_batch(chunk_texts, batch_size=10)

            # 8. Create DocumentChunk ORM instances
            db_chunks = []
            for chunk_data, vector in zip(chunks_data, embeddings):
                chunk_record = DocumentChunk(
                    organization_id=doc.organization_id,
                    knowledge_base_id=doc.knowledge_base_id,
                    document_id=doc.id,
                    chunk_index=chunk_data.chunk_index,
                    ingestion_version=doc.ingestion_version,
                    page_number=chunk_data.page_number,
                    text=chunk_data.text,
                    embedding=vector,
                )
                db_chunks.append(chunk_record)

            # Bulk save chunks
            self.db.add_all(db_chunks)

            # 9. Update status -> 'completed'
            doc.ingestion_status = "completed"
            doc.updated_at = datetime.now(timezone.utc)
            await self.db.commit()

            logger.info(
                "ingestion_completed",
                document_id=str(document_id),
                total_chunks=len(db_chunks),
            )
            return True

        except Exception as e:
            await self.db.rollback()
            
            # Record failure status
            doc.ingestion_status = "failed"
            doc.error_message = str(e)
            doc.updated_at = datetime.now(timezone.utc)
            await self.db.commit()

            logger.error(
                "ingestion_failed",
                document_id=str(document_id),
                error=str(e),
                exc_info=True,
            )
            return False
