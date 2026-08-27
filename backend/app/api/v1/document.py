import uuid
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document import (
    DocumentService,
    DocumentError,
    DocumentNotFoundError,
    FileValidationError,
)

router = APIRouter(tags=["Documents"])


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or TXT document and enqueue ingestion job",
)
async def upload_document(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc_service = DocumentService(db)
    try:
        file_bytes = await file.read()
        doc = await doc_service.upload_document(
            organization_id=current_user.organization_id,
            knowledge_base_id=kb_id,
            filename=file.filename or "file.txt",
            file_bytes=file_bytes,
        )
        return DocumentResponse.model_validate(doc)
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/documents/{doc_id}/reingest",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-trigger ingestion pipeline for a document",
)
async def reingest_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc_service = DocumentService(db)
    try:
        doc = await doc_service.reingest_document(
            organization_id=current_user.organization_id,
            document_id=doc_id,
        )
        return DocumentResponse.model_validate(doc)
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/knowledge-bases/{kb_id}/documents",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List all documents in a Knowledge Base",
)
async def list_documents(
    kb_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    doc_service = DocumentService(db)
    docs = await doc_service.list_documents(
        organization_id=current_user.organization_id,
        knowledge_base_id=kb_id,
        skip=skip,
        limit=limit,
    )
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document metadata by ID",
)
async def get_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc_service = DocumentService(db)
    try:
        doc = await doc_service.get_document_by_id(
            organization_id=current_user.organization_id,
            document_id=doc_id,
        )
        return DocumentResponse.model_validate(doc)
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document and its file on disk",
)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_service = DocumentService(db)
    try:
        await doc_service.delete_document(
            organization_id=current_user.organization_id,
            document_id=doc_id,
        )
        return {"message": "Document deleted successfully"}
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
