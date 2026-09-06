
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config.settings import settings

from .interface import DocumentSource, SourceType
from .pipeline import Pipeline
from ...repositories.document.repository import DocumentRepository


logger = logging.getLogger(__name__)


class DocumentIngestionService:

    def __init__(
        self,
        *,
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

    async def process(
        self,
        *,
        document_id: str,
        business_id: str,
        collection_type: str,
    ) -> dict[str, Any] | None:
        document_id = document_id.strip()
        business_id = business_id.strip()
        collection_type = collection_type.strip()

        if not document_id:
            raise ValueError(
                "document_id must not be empty"
            )

        if not business_id:
            raise ValueError(
                "business_id must not be empty"
            )

        if not collection_type:
            raise ValueError(
                "collection_type must not be empty"
            )

        document = await self._repository.get(
            document_id,
        )

        if document is None:
            logger.error(
                "[DOCUMENT INGESTION] Document not found "
                "document_id=%s",
                document_id,
            )
            return None

        collection = self._resolve_collection(
            collection_type,
        )

        storage_url = document.get(
            "storage_url",
        )

        if not isinstance(
            storage_url,
            str,
        ) or not storage_url.strip():
            raise ValueError(
                "Document storage_url must not be empty"
            )

        await self._repository.increment_attempt(
            document_id,
        )

        temp_file_path: str | None = None

        try:
            await self._repository.set_processing(
                document_id=document_id,
                processing_stage="processing_document",
            )

            temp_file_path = await self._download_document(
                storage_url=storage_url.strip(),
                filename=document.get(
                    "filename",
                ),
            )

            source = DocumentSource(
                value=temp_file_path,
                source_type=SourceType.FILE,
            )

            pipeline = Pipeline(
                namespace=business_id,
            )

            result = await pipeline.ingest(
                collection=collection,
                source=source,
            )

            await self._repository.set_ingestion_result(
                document_id=document_id,
                result=result,
            )

            document = await self._repository.set_available(
                document_id,
            )

            logger.info(
                "[DOCUMENT INGESTION] Ingestion successful "
                "document_id=%s business_id=%s "
                "collection_type=%s collection=%s",
                document_id,
                business_id,
                collection_type,
                collection,
            )

            return document

        except Exception as exc:
            logger.exception(
                "[DOCUMENT INGESTION] Ingestion failed "
                "document_id=%s business_id=%s "
                "collection_type=%s collection=%s",
                document_id,
                business_id,
                collection_type,
                collection,
            )

            return await self._repository.set_failed(
                document_id=document_id,
                error_message=str(exc),
            )

        finally:
            if temp_file_path is not None:
                try:
                    Path(temp_file_path).unlink(
                        missing_ok=True,
                    )
                except Exception:
                    logger.warning(
                        "[DOCUMENT INGESTION] Failed to remove "
                        "temporary file: %s",
                        temp_file_path,
                        exc_info=True,
                    )

    @staticmethod
    def _resolve_collection(
        collection_type: str,
    ) -> str:
        collection_map = {
            "knowledge": "knowledge",
        }

        collection = collection_map.get(
            collection_type.lower(),
        )

        if collection is None:
            raise ValueError(
                f"Unsupported collection_type: "
                f"{collection_type}"
            )

        return collection

    async def _download_document(
        self,
        *,
        storage_url: str,
        filename: str | None,
    ) -> str:
        object_key = self._extract_object_key(
            storage_url,
        )

        suffix = ""

        if isinstance(
            filename,
            str,
        ) and filename.strip():
            suffix = Path(
                filename.strip(),
            ).suffix

        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        )

        temp_file_path = temp_file.name

        try:
            temp_file.close()

            self._s3.download_file(
                settings.minio_bucket,
                object_key,
                temp_file_path,
            )

            return temp_file_path

        except (
            BotoCoreError,
            ClientError,
        ):
            try:
                os.unlink(
                    temp_file_path,
                )
            except OSError:
                pass

            raise

        except Exception:
            try:
                os.unlink(
                    temp_file_path,
                )
            except OSError:
                pass

            raise

    @staticmethod
    def _extract_object_key(
        storage_url: str,
    ) -> str:
        bucket = settings.minio_bucket

        marker = f"/{bucket}/"

        if marker not in storage_url:
            raise ValueError(
                "Invalid document storage_url"
            )

        object_key = storage_url.split(
            marker,
            1,
        )[1].strip()

        if not object_key:
            raise ValueError(
                "Document storage_url does not contain "
                "a valid object key"
            )

        return object_key
