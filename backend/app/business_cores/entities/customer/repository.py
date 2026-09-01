from __future__ import annotations

from typing import Any

from ...core.identity import Identity
from ...core.repository import BusinessObjectRepository
from ..repository import EntityRepository


class CustomerRepository(BusinessObjectRepository):

    def __init__(
        self,
        *,
        repository: EntityRepository | None = None,
    ) -> None:
        self.repository = (
            repository
            if repository is not None
            else EntityRepository()
        )

    async def resolve(
        self,
        *,
        business_id: str,
        object_type: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:

        return await self.repository.resolve(
            business_id=business_id,
            object_type=object_type,
            data=data,
            identities=identities,
        )

    async def update(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:

        return await self.repository.update(
            business_id=business_id,
            object_type=object_type,
            object_id=object_id,
            data=data,
            identities=identities,
        )

    async def get(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> dict[str, Any] | None:

        return await self.repository.get(
            business_id=business_id,
            object_type=object_type,
            object_id=object_id,
        )

    async def delete(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> bool:

        return await self.repository.delete(
            business_id=business_id,
            object_type=object_type,
            object_id=object_id,
        )

    async def list(
        self,
        *,
        business_id: str,
        object_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        return await self.repository.list(
            business_id=business_id,
            object_type=object_type,
            limit=limit,
            offset=offset,
        )

    async def search(
        self,
        *,
        business_id: str,
        object_type: str,
        filters,
        limit,
    ) -> list[dict[str, Any]]:
        ...

    async def inspect_database(
        self,
        *,
        business_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ...

    async def inspect_collection(
        self,
        *,
        business_id: str,
        collection: str,
    ) -> dict[str, Any]:
        ...

    async def inspect_collections(
        self,
        *,
        business_id: str,
        collections: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        ...

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

    async def profile_collection(
        self,
        *,
        business_id: str,
        collection: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        ...

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

    async def discover_relationships(
        self,
        *,
        business_id: str,
        collections: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def find_collections_path(
        self,
        *,
        business_id: str,
        from_collection: str,
        to_collection: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        ...

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
