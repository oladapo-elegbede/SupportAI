import uuid
from dataclasses import dataclass
from typing import List, Optional
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.document import Document
from app.services.embedding import EmbeddingService, get_embedding_service

logger = structlog.get_logger("supportai.retrieval")


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_number: int
    chunk_index: int
    text: str
    similarity_score: float


class RetrievalService:
    """Service for embedding queries and retrieving tenant-isolated document chunks from pgvector."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: Optional[EmbeddingService] = None,
        top_k: int = 3,
        similarity_threshold: float = 0.0,
    ):
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def retrieve_relevant_chunks(
        self,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_text: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """
        Embeds query text and retrieves top-k relevant document chunks
        from pgvector filtered by organization_id and knowledge_base_id.
        """
        if not query_text.strip():
            return []

        k = top_k or self.top_k
        threshold = similarity_threshold if similarity_threshold is not None else self.similarity_threshold

        logger.info(
            "rag_retrieval_started",
            organization_id=str(organization_id),
            knowledge_base_id=str(knowledge_base_id),
            query_length=len(query_text),
            top_k=k,
            threshold=threshold,
        )

        # 1. Embed query text using nomic-embed-text
        query_vector = await self.embedding_service.embed_text(query_text)

        # 2. Cosine Distance Operator (<=>)
        cosine_dist = DocumentChunk.embedding.cosine_distance(query_vector)

        # 3. Query PostgreSQL with tenant isolation and completed document status filter
        stmt = (
            select(
                DocumentChunk,
                Document.filename,
                cosine_dist.label("distance"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.organization_id == organization_id,
                DocumentChunk.knowledge_base_id == knowledge_base_id,
                Document.ingestion_status == "completed",
            )
            .order_by(cosine_dist.asc())
            .limit(k)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        retrieved_chunks: List[RetrievedChunk] = []
        for chunk, filename, dist in rows:
            # Cosine Similarity = 1.0 - Cosine Distance
            similarity = max(0.0, 1.0 - float(dist))
            
            if similarity >= threshold:
                retrieved_chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        filename=filename,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        similarity_score=round(similarity, 4),
                    )
                )

        logger.info(
            "rag_retrieval_completed",
            chunks_retrieved=len(retrieved_chunks),
            top_score=retrieved_chunks[0].similarity_score if retrieved_chunks else 0.0,
        )

        return retrieved_chunks
