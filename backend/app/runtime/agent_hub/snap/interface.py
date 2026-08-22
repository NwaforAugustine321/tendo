from __future__ import annotations

from abc import ABC, abstractmethod

from .models import SnapModel, SnapRecord


class SnapI(ABC):

    @abstractmethod
    async def create(
        self,
        *,
        business_id: str,
        snap: SnapModel,
    ) -> SnapRecord:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def list(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> list[SnapRecord]:
        raise NotImplementedError

    @abstractmethod
    async def get_active(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> list[SnapRecord]:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def complete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord:
        raise NotImplementedError

    @abstractmethod
    async def refresh(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> bool:
        raise NotImplementedError
