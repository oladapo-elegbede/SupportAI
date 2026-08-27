import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Knowledge Base name")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
