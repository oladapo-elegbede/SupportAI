import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Customer question text")
    session_id: Optional[str] = Field(None, max_length=100, description="Optional session tracking ID")


class SourceCitation(BaseModel):
    document_name: str
    page_number: int
    similarity_score: float


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    session_id: str
    message: MessageResponse
    sources: List[SourceCitation] = []


class ConversationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    session_id: str
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
