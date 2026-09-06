
from __future__ import annotations

from typing import Any, Mapping, Sequence

from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo_client import get_client

from .interface import MongoRepositoryInterface


class MongoRepository(MongoRepositoryInterface):
    def __init__(self, collection: str) -> None:
        if not collection or not collection.strip():
            raise ValueError("collection must not be empty")

        self._collection: AsyncCollection = get_client()[collection.strip()]

    async def create(
        self,
        data: Mapping[str, Any],
    ) -> dict[str, Any]:
        document = dict(data)

        await self._collection.insert_one(document)

        return document

    async def create_many(
        self,
        data: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        documents = [dict(item) for item in data]

        if not documents:
            return []

        await self._collection.insert_many(documents)

        return documents

    async def get_by_id(
        self,
        document_id: Any,
    ) -> dict[str, Any] | None:
        return await self._collection.find_one(
            {"id": document_id}
        )

    async def find_one(
        self,
        filters: Mapping[str, Any],
        projection: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return await self._collection.find_one(
            dict(filters),
            projection,
        )

    async def find_many(
        self,
        filters: Mapping[str, Any] | None = None,
        projection: Mapping[str, Any] | None = None,
        *,
        skip: int = 0,
        limit: int | None = None,
        sort: Sequence[tuple[str, int]] | None = None,
    ) -> list[dict[str, Any]]:
        if skip < 0:
            raise ValueError("skip must be greater than or equal to 0")

        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than 0")

        cursor = self._collection.find(
            dict(filters or {}),
            projection,
        )

        if sort:
            cursor = cursor.sort(list(sort))

        cursor = cursor.skip(skip)

        if limit is not None:
            cursor = cursor.limit(limit)

        return await cursor.to_list()

    async def update_one(
        self,
        filters: Mapping[str, Any],
        updates: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> dict[str, Any] | None:
        return await self._collection.find_one_and_update(
            dict(filters),
            {"$set": dict(updates)},
            upsert=upsert,
            return_document=ReturnDocument.AFTER,
        )

    async def update_many(
        self,
        filters: Mapping[str, Any],
        updates: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> int:
        result = await self._collection.update_many(
            dict(filters),
            {"$set": dict(updates)},
            upsert=upsert,
        )

        return result.modified_count

    async def replace_one(
        self,
        filters: Mapping[str, Any],
        replacement: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> dict[str, Any] | None:
        await self._collection.replace_one(
            dict(filters),
            dict(replacement),
            upsert=upsert,
        )

        return await self._collection.find_one(
            dict(filters)
        )

    async def delete_one(
        self,
        filters: Mapping[str, Any],
    ) -> bool:
        result = await self._collection.delete_one(
            dict(filters)
        )

        return result.deleted_count > 0

    async def delete_many(
        self,
        filters: Mapping[str, Any],
    ) -> int:
        result = await self._collection.delete_many(
            dict(filters)
        )

        return result.deleted_count

    async def count(
        self,
        filters: Mapping[str, Any] | None = None,
    ) -> int:
        return await self._collection.count_documents(
            dict(filters or {})
        )

    async def exists(
        self,
        filters: Mapping[str, Any],
    ) -> bool:
        return (
            await self._collection.find_one(
                dict(filters),
                {"_id": 1},
            )
            is not None
        )

    async def distinct(
        self,
        field: str,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        return await self._collection.distinct(
            field,
            dict(filters or {}),
        )

    async def aggregate(
        self,
        pipeline: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        cursor = self._collection.aggregate(
            list(pipeline)
        )

        return await cursor.to_list()

    async def create_index(
        self,
        keys: str | Sequence[tuple[str, int]],
        *,
        unique: bool = False,
        sparse: bool = False,
        name: str | None = None,
    ) -> str:
        return await self._collection.create_index(
            keys,
            unique=unique,
            sparse=sparse,
            name=name,
        )

    async def drop_index(
        self,
        index_name: str,
    ) -> None:
        await self._collection.drop_index(index_name)
