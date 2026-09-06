
from __future__ import annotations

from typing import Any

from ..worker import BackgroundWorker
from ...services.ingestions.service import DocumentIngestionService
from ...repositories.document.repository import DocumentRepository


class DocumentProcessorWorker(
    BackgroundWorker,
):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            job_type="document_processing",
            worker_name="document-processing",
        )

        self._document_ingestion_service = (
            DocumentIngestionService(
                repository=DocumentRepository(),
            )
        )

    async def process(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any] | None:
        payload = self.get_payload(
            job,
        )

        document_id = payload.get(
            "document_id",
        )

        business_id = payload.get(
            "business_id",
        )

        collection_type = payload.get(
            "collection_type",
        )

        if not isinstance(
            document_id,
            str,
        ) or not document_id.strip():
            raise ValueError(
                "'document_id' cannot be empty.",
            )

        if not isinstance(
            business_id,
            str,
        ) or not business_id.strip():
            raise ValueError(
                "'business_id' cannot be empty.",
            )

        if not isinstance(
            collection_type,
            str,
        ) or not collection_type.strip():
            raise ValueError(
                "'collection_type' cannot be empty.",
            )

        return await self._document_ingestion_service.process(
            document_id=document_id.strip(),
            business_id=business_id.strip(),
            collection_type=collection_type.strip(),
        )
