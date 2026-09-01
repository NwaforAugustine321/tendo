from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .identity import Identity


class BusinessObjectRepository(ABC):

    @abstractmethod
    async def resolve(
        self,
        *,
        business_id: str,
        object_type: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def update(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def delete(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> bool:
        ...

    @abstractmethod
    async def list(
        self,
        *,
        business_id: str,
        object_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def search(
        self,
        *,
        business_id: str,
        object_type: str,
        filters: dict[str, Any],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def inspect_database(
        self,
        *,
        business_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def inspect_collection(
        self,
        *,
        business_id: str,
        collection: str,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def inspect_collections(
        self,
        *,
        business_id: str,
        collections: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def query_collection(
        self,
        *,
        business_id: str,
        collection: str,
        filters: dict[str, Any],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def profile_collection(
        self,
        *,
        business_id: str,
        collection: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def search_business_data(
        self,
        *,
        business_id: str,
        collection: str,
        query: str,
        search_type: str,
        fields: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def discover_relationships(
        self,
        *,
        business_id: str,
        collections: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def find_collections_path(
        self,
        *,
        business_id: str,
        from_collection: str,
        to_collection: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def aggregate_collection(
        self,
        *,
        business_id: str,
        collection: str,
        filters: dict[str, Any],
        group_by: list[str],
        metrics: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def aggregate_related_data(
        self,
        *,
        business_id: str,
        collections: list[str],
        relationship: dict[str, str],
        filters: dict[str, Any],
        group_by: list[str],
        metrics: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def traverse_relationships(
        self,
        *,
        business_id: str,
        start_collection: str,
        relationships: list[dict[str, str]],
        filters: dict[str, Any],
        fields: list[str],
        limit: int = 20,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        ...
