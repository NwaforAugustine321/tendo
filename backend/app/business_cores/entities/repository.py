from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.db.mongo_client import get_client

from ..core.identity import Identity
from ..core.repository import BusinessObjectRepository


class EntityRepository(BusinessObjectRepository):

    def __init__(
        self,
        *,
        db: AsyncDatabase | None = None,
    ) -> None:
        self.db = db or get_client()

    def _collection(
        self,
        object_type: str,
    ):
        if not object_type:
            raise ValueError(
                "Entity object_type cannot be empty"
            )

        return self.db[object_type]

    async def resolve(
        self,
        *,
        business_id: str,
        object_type: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:

        if not business_id:
            raise ValueError(
                "business_id cannot be empty"
            )

        collection = self._collection(object_type)

        for identity in identities:
            document = await collection.find_one(
                {
                    "business_id": business_id,
                    "identities.identifier_hash": (
                        identity.identifier_hash
                    ),
                },
                {
                    "_id": 1,
                    "status": 1,
                },
            )

            if document is not None:
                return {
                    "id": str(document["_id"]),
                    "created": False,
                    "status": document.get(
                        "status",
                        "active",
                    ),
                }

        object_id = str(uuid4())
        now = datetime.now(timezone.utc)

        document = {
            "_id": object_id,
            "business_id": business_id,
            "data": data,
            "identities": self._identity_documents(
                identities
            ),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

        try:
            await collection.insert_one(document)

        except DuplicateKeyError:

            for identity in identities:
                existing = await collection.find_one(
                    {
                        "business_id": business_id,
                        "identities.identifier_hash": (
                            identity.identifier_hash
                        ),
                    },
                    {
                        "_id": 1,
                        "status": 1,
                    },
                )

                if existing is not None:
                    return {
                        "id": str(existing["_id"]),
                        "created": False,
                        "status": existing.get(
                            "status",
                            "active",
                        ),
                    }

            raise

        return {
            "id": object_id,
            "created": True,
            "status": "active",
        }

    async def update(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:

        collection = self._collection(object_type)

        now = datetime.now(timezone.utc)

        result = await collection.update_one(
            {
                "_id": object_id,
                "business_id": business_id,
            },
            {
                "$set": {
                    "data": data,
                    "identities": self._identity_documents(
                        identities
                    ),
                    "updated_at": now,
                },
            },
        )

        if result.matched_count == 0:
            raise ValueError(
                f"{object_type} not found: {object_id}"
            )

        document = await collection.find_one(
            {
                "_id": object_id,
                "business_id": business_id,
            },
            {
                "status": 1,
            },
        )

        return {
            "id": object_id,
            "status": (
                document.get(
                    "status",
                    "active",
                )
                if document
                else "active"
            ),
        }

    async def get(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> dict[str, Any] | None:

        collection = self._collection(object_type)

        document = await collection.find_one(
            {
                "_id": object_id,
                "business_id": business_id,
            }
        )

        if document is None:
            return None

        document["_id"] = str(
            document["_id"]
        )

        return document

    async def delete(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> bool:

        collection = self._collection(object_type)

        result = await collection.delete_one(
            {
                "_id": object_id,
                "business_id": business_id,
            }
        )

        return result.deleted_count > 0

    async def list(
        self,
        *,
        business_id: str,
        object_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        collection = self._collection(object_type)

        limit = max(
            1,
            min(limit, 500),
        )

        offset = max(
            0,
            offset,
        )

        cursor = (
            collection
            .find(
                {
                    "business_id": business_id,
                }
            )
            .sort(
                "created_at",
                ASCENDING,
            )
            .skip(offset)
            .limit(limit)
        )

        documents = await cursor.to_list(
            length=limit,
        )

        for document in documents:
            document["_id"] = str(
                document["_id"]
            )

        return documents

    async def ensure_indexes(
        self,
        object_type: str,
    ) -> None:

        collection = self._collection(object_type)

        await collection.create_index(
            [
                ("business_id", ASCENDING),
                ("created_at", ASCENDING),
            ],
            name="business_created_at",
        )

        await collection.create_index(
            [
                ("business_id", ASCENDING),
                (
                    "identities.identifier_hash",
                    ASCENDING,
                ),
            ],
            unique=True,
            sparse=True,
            name="business_identity",
        )

    @staticmethod
    def _identity_documents(
        identities: list[Identity],
    ) -> list[dict[str, str]]:

        return [
            {
                "identifier_type": identity.identifier_type,
                "identifier_key": identity.identifier_key,
                "identifier_hash": identity.identifier_hash,
            }
            for identity in identities
        ]
