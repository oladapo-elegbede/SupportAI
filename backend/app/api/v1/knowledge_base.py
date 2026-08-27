import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
)
from app.services.knowledge_base import (
    KBService,
    KBError,
    KBNotFoundError,
    KBAlreadyExistsError,
)

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Bases"])


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Knowledge Base",
)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseResponse:
    kb_service = KBService(db)
    try:
        kb = await kb_service.create_kb(current_user.organization_id, data)
        return KnowledgeBaseResponse(
            id=kb.id,
            organization_id=kb.organization_id,
            name=kb.name,
            description=kb.description,
            document_count=0,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
        )
    except KBAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "",
    response_model=List[KnowledgeBaseResponse],
    status_code=status.HTTP_200_OK,
    summary="List all Knowledge Bases for the current organization",
)
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[KnowledgeBaseResponse]:
    kb_service = KBService(db)
    kb_tuples = await kb_service.list_kbs(current_user.organization_id, skip=skip, limit=limit)
    return [
        KnowledgeBaseResponse(
            id=kb.id,
            organization_id=kb.organization_id,
            name=kb.name,
            description=kb.description,
            document_count=doc_count,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
        )
        for kb, doc_count in kb_tuples
    ]


@router.get(
    "/{kb_id}",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Knowledge Base details by ID",
)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseResponse:
    kb_service = KBService(db)
    try:
        kb = await kb_service.get_kb_by_id(current_user.organization_id, kb_id)
        
        # Count documents for this KB
        doc_count = await db.scalar(
            select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
        ) or 0

        return KnowledgeBaseResponse(
            id=kb.id,
            organization_id=kb.organization_id,
            name=kb.name,
            description=kb.description,
            document_count=doc_count,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
        )
    except KBNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{kb_id}",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Knowledge Base name or description",
)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    data: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseResponse:
    kb_service = KBService(db)
    try:
        kb = await kb_service.update_kb(current_user.organization_id, kb_id, data)
        
        doc_count = await db.scalar(
            select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
        ) or 0

        return KnowledgeBaseResponse(
            id=kb.id,
            organization_id=kb.organization_id,
            name=kb.name,
            description=kb.description,
            document_count=doc_count,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
        )
    except KBNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except KBAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{kb_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a Knowledge Base and all its documents",
)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb_service = KBService(db)
    try:
        await kb_service.delete_kb(current_user.organization_id, kb_id)
        return {"message": "Knowledge Base deleted successfully"}
    except KBNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
