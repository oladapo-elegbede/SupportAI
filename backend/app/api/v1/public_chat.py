import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.chat import ChatService, ChatError

router = APIRouter(prefix="/public", tags=["Public Chat Widget"])

# In-memory IP rate limiter: 10 requests per minute per IP address
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/chat/{kb_id}",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Public Customer Chat Endpoint (Unauthenticated)",
)
@limiter.limit("10/minute")
async def send_public_chat_message(
    request: Request,
    kb_id: uuid.UUID,
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """
    Unauthenticated public endpoint for end customers chatting via the widget.
    Resolves tenant organization_id automatically from the knowledge_base_id.
    """
    # 1. Resolve Knowledge Base and Organization ID
    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Base not found.",
        )

    # 2. Execute RAG Chat via ChatService
    chat_service = ChatService(db)
    try:
        return await chat_service.send_message(
            organization_id=kb.organization_id,
            knowledge_base_id=kb.id,
            req=body,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Public chat processing error: {str(e)}",
        )
