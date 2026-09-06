
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.services.documents import DocumentRepository, DocumentService


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def get_document_service() -> DocumentService:
    return DocumentService(
        repository=DocumentRepository(),
    )


@router.post("/upload")
async def upload_document(
    business_id: str = Form(...),
    user_id: str | None = Form(None),
    entity_type: str | None = Form(None),
    entity_id: str | None = Form(None),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    service = get_document_service()

    return await service.upload(
        business_id=business_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        file=file,
    )


@router.get("")
async def list_documents(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, gt=0),
) -> list[dict[str, Any]]:
    service = get_document_service()

    return await service.list(
        offset=offset,
        limit=limit,
    )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
) -> dict[str, Any]:
    service = get_document_service()

    document = await service.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
) -> dict[str, Any]:
    service = get_document_service()

    deleted = await service.delete(document_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return {
        "document_id": document_id,
        "message": "Document deleted successfully",
    }
