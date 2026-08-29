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
