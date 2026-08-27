import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    file_path: str
    file_type: str
    file_size_bytes: int
    ingestion_status: str
    ingestion_version: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
