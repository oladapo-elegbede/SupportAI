import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.organization import Organization
from app.models.knowledge_base import KnowledgeBase
from app.services.retrieval import RetrievalService, RetrievedChunk
from app.services.llm import LLMService, PromptBuilder, get_llm_service
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    MessageResponse,
    SourceCitation,
)

logger = structlog.get_logger("supportai.chat")


class ChatError(Exception):
    """Base exception for Chat operations."""
    pass


class ChatService:
    """Orchestrates end-to-end RAG chat: session lookup, context retrieval, LLM response, citation mapping, and DB persistence."""

    def __init__(
        self,
        db: AsyncSession,
        retrieval_service: Optional[RetrievalService] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.db = db
        self.retrieval_service = retrieval_service or RetrievalService(db)
        self.llm_service = llm_service or get_llm_service()

    async def get_or_create_conversation(
        self,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        session_id: str,
        first_query: str,
    ) -> Conversation:
        """Finds existing conversation by session_id or creates a new one."""
        convo = await self.db.scalar(
            select(Conversation).where(
                Conversation.organization_id == organization_id,
                Conversation.knowledge_base_id == knowledge_base_id,
                Conversation.session_id == session_id,
            )
        )
        if not convo:
            title = first_query.strip()[:50] + ("..." if len(first_query) > 50 else "")
            convo = Conversation(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                session_id=session_id,
                title=title if title else "New Conversation",
            )
            self.db.add(convo)
            await self.db.commit()
            await self.db.refresh(convo)
        return convo

    async def get_conversation_history(
        self, conversation_id: uuid.UUID, limit: int = 6
    ) -> List[dict]:
        """Fetches recent conversation history formatted for prompt context."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = list(reversed(result.scalars().all()))
        return [
            {"role": "user" if m.sender_type == "user" else "assistant", "content": m.content}
            for m in messages
        ]

    async def send_message(
        self,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        req: ChatMessageRequest,
    ) -> ChatMessageResponse:
        """Executes full RAG chat pipeline and persists user query and grounded AI answer."""
        
        # 1. Fetch Organization for company name in prompt
        org = await self.db.scalar(select(Organization).where(Organization.id == organization_id))
        company_name = org.name if org else "our company"

        # 2. Resolve Session & Conversation
        session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
        convo = await self.get_or_create_conversation(
            organization_id, knowledge_base_id, session_id, req.message
        )

        # 3. Persist User Message
        user_msg = Message(
            conversation_id=convo.id,
            sender_type="user",
            content=req.message.strip(),
        )
        self.db.add(user_msg)
        await self.db.commit()

        # 4. Fetch Recent History for Context
        history = await self.get_conversation_history(convo.id, limit=6)

        # 5. Retrieve Context Chunks from pgvector
        retrieved_chunks = await self.retrieval_service.retrieve_relevant_chunks(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            query_text=req.message,
            top_k=3,
        )

        # 6. Build Hardened System & User Prompt
        sys_prompt, user_prompt = PromptBuilder.build_rag_prompt(
            company_name=company_name,
            query=req.message,
            retrieved_chunks=retrieved_chunks,
            conversation_history=history,
        )

        # 7. Generate Response via Local LLM (qwen2.5:3b)
        ai_response_text = await self.llm_service.generate_response(
            prompt=user_prompt,
            system_prompt=sys_prompt,
        )

        # 8. Extract Sources Array for Response
        sources_list = [
            {
                "document_name": chunk.filename,
                "page_number": chunk.page_number,
                "similarity_score": chunk.similarity_score,
            }
            for chunk in retrieved_chunks
        ]
        
        source_citations = [
            SourceCitation(
                document_name=s["document_name"],
                page_number=s["page_number"],
                similarity_score=s["similarity_score"],
            )
            for s in sources_list
        ]

        # 9. Persist Assistant Response in DB
        assistant_msg = Message(
            conversation_id=convo.id,
            sender_type="assistant",
            content=ai_response_text,
            sources=sources_list if sources_list else None,
        )
        self.db.add(assistant_msg)
        
        # Touch conversation updated_at
        convo.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(assistant_msg)

        return ChatMessageResponse(
            conversation_id=convo.id,
            session_id=convo.session_id,
            message=MessageResponse.model_validate(assistant_msg),
            sources=source_citations,
        )

    async def list_conversations(
        self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[Tuple[Conversation, int]]:
        """Lists tenant conversations with message counts."""
        stmt = (
            select(Conversation, func.count(Message.id).label("msg_count"))
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.organization_id == organization_id)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_conversation_messages(
        self, organization_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Tuple[Conversation, List[Message]]:
        convo = await self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.organization_id == organization_id,
            )
        )
        if not convo:
            raise ChatError("Conversation not found.")

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = list(result.scalars().all())
        return convo, messages
