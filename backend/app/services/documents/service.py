
from __future__ import annotations

import logging
import os
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile
from pymongo import ReturnDocument

from ...config.settings import settings
from ...repositories.document.repository import DocumentRepository


logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
    ) -> None:
        self._repository = repository

        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(
                signature_version="s3v4",
            ),
        )

    async def upload(
        self,
        *,
        business_id: str,
        user_id: str | None,
        entity_type: str | None,
        entity_id: str | None,
        file: UploadFile,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        business_id = business_id.strip()

        if not business_id:
            raise HTTPException(
                status_code=400,
                detail="business_id is required",
            )

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="A filename is required",
            )

        original_filename = file.filename
        filename = os.path.basename(original_filename)

        if not filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename",
            )

        try:
            current_position = file.file.tell()
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(current_position)
        except (OSError, AttributeError) as exc:
            logger.exception(
                "[DOCUMENT UPLOAD] Failed to determine file size "
                "business_id=%s filename=%s",
                business_id,
                filename,
            )

            raise HTTPException(
                status_code=400,
                detail="Unable to determine file size",
            ) from exc

        document_metadata = dict(metadata or {})

        document_metadata.setdefault(
            "source",
            "upload",
        )

        document_metadata.setdefault(
            "filename",
            original_filename,
        )

        document_metadata.setdefault(
            "file_size",
            file_size,
        )

        document = {
            "business_id": business_id,
            "user_id": user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "filename": filename,
            "original_filename": original_filename,
            "mime_type": (
                file.content_type
                or "application/octet-stream"
            ),
            "file_size": file_size,
            "storage_url": None,
            "status": "uploading",
            "processing_stage": "uploading",
            "attempt_count": 0,
            "error_message": None,
            "metadata": document_metadata,
        }

        document = await self._repository.create(document)

        document_id = str(document["_id"])

        await self._repository.update_one(
            {"_id": document["_id"]},
            {
                "id": document_id,
            },
        )

        object_key = (
            f"{business_id}/"
            f"{document_id}/"
            f"{filename}"
        )

        logger.info(
            "[DOCUMENT UPLOAD] Uploading "
            "business_id=%s document_id=%s "
            "bucket=%s key=%s size=%s",
            business_id,
            document_id,
            settings.minio_bucket,
            object_key,
            file_size,
        )

        try:
            self._s3.upload_fileobj(
                file.file,
                settings.minio_bucket,
                object_key,
                ExtraArgs={
                    "ContentType": (
                        file.content_type
                        or "application/octet-stream"
                    ),
                },
            )

        except (BotoCoreError, ClientError) as exc:
            logger.exception(
                "[DOCUMENT UPLOAD] MinIO upload failed "
                "business_id=%s document_id=%s key=%s",
                business_id,
                document_id,
                object_key,
            )

            await self._repository.set_failed(
                document_id=document_id,
                error_message="Failed to upload document to object storage",
            )

            raise HTTPException(
                status_code=500,
                detail="Failed to upload document to object storage",
            ) from exc

        except Exception as exc:
            logger.exception(
                "[DOCUMENT UPLOAD] Unexpected upload error "
                "business_id=%s document_id=%s key=%s",
                business_id,
                document_id,
                object_key,
            )

            await self._repository.set_failed(
                document_id=document_id,
                error_message="Unexpected error while uploading document",
            )

            raise HTTPException(
                status_code=500,
                detail="Unexpected error while uploading document",
            ) from exc

        finally:
            await file.close()

        document_url = (
            f"{settings.minio_public_endpoint.rstrip('/')}/"
            f"{settings.minio_bucket}/"
            f"{object_key}"
        )

        document = await self._repository.update_one(
            {"id": document_id},
            {
                "storage_url": document_url,
                "status": "uploaded",
                "processing_stage": "waiting_for_ingestor",
            },
        )

        logger.info(
            "[DOCUMENT UPLOAD] Successfully uploaded "
            "business_id=%s document_id=%s key=%s",
            business_id,
            document_id,
            object_key,
        )

        return document

    async def get(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self._repository.get(document_id)

    async def set_processing(
        self,
        document_id: str,
        processing_stage: str,
    ) -> dict[str, Any] | None:
        return await self._repository.set_processing(
            document_id=document_id,
            processing_stage=processing_stage,
        )

    async def set_available(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self._repository.set_available(
            document_id=document_id,
        )

    async def set_failed(
        self,
        document_id: str,
        error_message: str,
    ) -> dict[str, Any] | None:
        return await self._repository.set_failed(
            document_id=document_id,
            error_message=error_message,
        )

    async def increment_attempt(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self._repository.increment_attempt(
            document_id=document_id,
        )

    async def retry(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self._repository.reset_for_retry(
            document_id=document_id,
        )

    async def delete(
        self,
        document_id: str,
    ) -> bool:
        return await self._repository.delete(
            document_id=document_id,
        )

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail="offset must be greater than or equal to 0",
            )

        if limit <= 0:
            raise HTTPException(
                status_code=400,
                detail="limit must be greater than 0",
            )

        return await self._repository.find_many(
            {},
            skip=offset,
            limit=limit,
        )
