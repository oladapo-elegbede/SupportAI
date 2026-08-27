import io
import uuid
import pytest
import httpx
from sqlalchemy import select, delete

from tests.conftest import TestAsyncSessionLocal
from app.models.organization import Organization
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.extractor import TextExtractorService, ExtractionError
from app.services.chunker import TextChunkerService
from app.services.embedding import get_embedding_service
from app.services.ingestion import IngestionService
from app.services.storage import LocalFileStorage


async def clean_ingestion_data(slug: str):
    """Helper to clean up test orgs, documents, vector chunks, and files on disk."""
    async with TestAsyncSessionLocal() as session:
        org = await session.scalar(select(Organization).where(Organization.slug == slug))
        if org:
            storage = LocalFileStorage("./uploads")
            await storage.delete_directory(str(org.id))
            await session.execute(delete(Organization).where(Organization.id == org.id))
            await session.commit()
        await session.close()


# ============================================================================
# 1. TEXT EXTRACTOR & CHUNKER UNIT TESTS
# ============================================================================

def test_text_cleaner_and_chunker_logic():
    chunker = TextChunkerService(chunk_size=100, chunk_overlap=20)
    
    raw = "Hello\x00 World!\n\n\n\nSupportAI   uses   pgvector."
    cleaned = chunker.clean_text(raw)
    assert "\x00" not in cleaned
    assert "\n\n\n" not in cleaned

    pages = [
        (1, "Page 1 contains information about grounded customer support RAG responses."),
        (2, "Page 2 outlines the refund policy and subscription billing details."),
    ]
    chunks = chunker.chunk_document_pages(pages)
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0


@pytest.mark.asyncio
async def test_pdf_extractor_valid_and_corrupt():
    extractor = TextExtractorService()

    txt_pages = await extractor.extract_text(b"Simple plain text file for testing.", "txt")
    assert len(txt_pages) == 1
    assert txt_pages[0][0] == 1

    with pytest.raises(ExtractionError):
        await extractor.extract_text(b"%PDF-1.4 Corrupted Invalid Header Bytes", "pdf")


# ============================================================================
# 2. LOCAL EMBEDDING SERVICE UNIT TEST
# ============================================================================

@pytest.mark.asyncio
async def test_ollama_embedding_service_dimensions():
    service = get_embedding_service()
    assert service.dimensions == 768

    vector = await service.embed_text("SupportAI stores vectors using pgvector.")
    assert len(vector) == 768
    assert isinstance(vector[0], float)


# ============================================================================
# 3. END-TO-END INGESTION PIPELINE & IDEMPOTENCY TEST
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_ingestion_and_idempotency():
    slug = "ingestion-test-corp"
    await clean_ingestion_data(slug)

    async with TestAsyncSessionLocal() as session:
        org = Organization(name="Ingestion Test Corp", slug=slug)
        session.add(org)
        await session.commit()

        kb = KnowledgeBase(organization_id=org.id, name="Support Manuals")
        session.add(kb)
        await session.commit()

        doc_id = uuid.uuid4()
        file_bytes = b"SupportAI uses nomic-embed-text for 768-dimensional embeddings.\n\nAll vector chunks are stored in PostgreSQL using pgvector."
        rel_path = f"{org.id}/{kb.id}/{doc_id}.txt"

        storage = LocalFileStorage("./uploads")
        await storage.save_file(file_bytes, rel_path)

        doc = Document(
            id=doc_id,
            organization_id=org.id,
            knowledge_base_id=kb.id,
            filename="manual.txt",
            file_path=rel_path,
            file_type="txt",
            file_size_bytes=len(file_bytes),
            ingestion_status="uploaded",
        )
        session.add(doc)
        await session.commit()

        ingestion_service = IngestionService(session, storage=storage)
        success = await ingestion_service.process_document(doc_id, org.id)
        assert success is True

        await session.refresh(doc)
        assert doc.ingestion_status == "completed"

        stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
        chunks = (await session.execute(stmt)).scalars().all()
        assert len(chunks) >= 1
        assert len(chunks[0].embedding) == 768

        retry_success = await ingestion_service.process_document(doc_id, org.id)
        assert retry_success is True

        retry_chunks = (await session.execute(stmt)).scalars().all()
        assert len(retry_chunks) == len(chunks)

        await session.close()

    await clean_ingestion_data(slug)
