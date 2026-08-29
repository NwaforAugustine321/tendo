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
