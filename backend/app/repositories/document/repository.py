
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.mongodb.repository import MongoRepository


class DocumentRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("documents")

    async def create(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        document = {
            **data,
            "created_at": now,
            "updated_at": now,
        }

        return await super().create(document)

    async def get(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self.find_one(
            {"id": document_id}
        )

    async def set_processing(
        self,
        document_id: str,
        processing_stage: str,
    ) -> dict[str, Any] | None:
        return await self.update_one(
            {"id": document_id},
            {
                "status": "processing",
                "processing_stage": processing_stage,
                "updated_at": datetime.now(timezone.utc),
            },
        )

    async def set_available(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self.update_one(
            {"id": document_id},
            {
                "status": "available",
                "processing_stage": "completed",
                "error_message": None,
                "updated_at": datetime.now(timezone.utc),
            },
        )

    async def set_failed(
        self,
        document_id: str,
        error_message: str,
    ) -> dict[str, Any] | None:
        return await self.update_one(
            {"id": document_id},
            {
                "status": "failed",
                "error_message": error_message,
                "updated_at": datetime.now(timezone.utc),
            },
        )

    async def increment_attempt(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self._collection.find_one_and_update(
            {"id": document_id},
            {
                "$inc": {
                    "attempt_count": 1,
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            return_document=True,
        )

    async def reset_for_retry(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        return await self.update_one(
            {"id": document_id},
            {
                "status": "uploaded",
                "processing_stage": "waiting_for_ingestor",
                "error_message": None,
                "updated_at": datetime.now(timezone.utc),
            },
        )

    async def delete(
        self,
        document_id: str,
    ) -> bool:
        return await self.delete_one(
            {"id": document_id}
        )
