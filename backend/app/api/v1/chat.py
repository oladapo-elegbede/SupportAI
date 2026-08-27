import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.chat import ChatService, ChatError
from app.services.knowledge_base import KBService, KBNotFoundError

router = APIRouter(tags=["Chat & Conversations"])


@router.post(
    "/knowledge-bases/{kb_id}/chat",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a grounded RAG chat message (Authenticated Admin)",
)
async def send_admin_chat_message(
    kb_id: uuid.UUID,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    # 1. Verify Knowledge Base belongs to tenant
    kb_service = KBService(db)
    try:
        await kb_service.get_kb_by_id(current_user.organization_id, kb_id)
    except KBNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # 2. Execute RAG Chat via ChatService
    chat_service = ChatService(db)
    try:
        return await chat_service.send_message(
            organization_id=current_user.organization_id,
            knowledge_base_id=kb_id,
            req=request,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation error: {str(e)}",
        )


@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List all chat conversations for the current organization",
)
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    chat_service = ChatService(db)
    convo_tuples = await chat_service.list_conversations(
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    return [
        ConversationResponse(
            id=convo.id,
            organization_id=convo.organization_id,
            knowledge_base_id=convo.knowledge_base_id,
            session_id=convo.session_id,
            title=convo.title,
            message_count=msg_count,
            created_at=convo.created_at,
            updated_at=convo.updated_at,
        )
        for convo, msg_count in convo_tuples
    ]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get full message history for a conversation",
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MessageResponse]:
    chat_service = ChatService(db)
    try:
        convo, messages = await chat_service.get_conversation_messages(
            organization_id=current_user.organization_id,
            conversation_id=conversation_id,
        )
        return [MessageResponse.model_validate(m) for m in messages]
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
