
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence


class MongoRepositoryInterface(ABC):
    @abstractmethod
    async def create(
        self,
        data: Mapping[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def create_many(
        self,
        data: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        document_id: Any,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def find_one(
        self,
        filters: Mapping[str, Any],
        projection: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def find_many(
        self,
        filters: Mapping[str, Any] | None = None,
        projection: Mapping[str, Any] | None = None,
        *,
        skip: int = 0,
        limit: int | None = None,
        sort: Sequence[tuple[str, int]] | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def update_one(
        self,
        filters: Mapping[str, Any],
        updates: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def update_many(
        self,
        filters: Mapping[str, Any],
        updates: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def replace_one(
        self,
        filters: Mapping[str, Any],
        replacement: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_one(
        self,
        filters: Mapping[str, Any],
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete_many(
        self,
        filters: Mapping[str, Any],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def count(
        self,
        filters: Mapping[str, Any] | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        filters: Mapping[str, Any],
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def distinct(
        self,
        field: str,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    async def aggregate(
        self,
        pipeline: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def create_index(
        self,
        keys: str | Sequence[tuple[str, int]],
        *,
        unique: bool = False,
        sparse: bool = False,
        name: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def drop_index(
        self,
        index_name: str,
    ) -> None:
        raise NotImplementedError
