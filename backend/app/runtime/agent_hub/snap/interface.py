from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .models import SnapModel, SnapRecord, SnapStatus, SnapType


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
    async def query(
        self,
        *,
        business_id: str,
        limit: int,
        statuses: Sequence[SnapStatus] | None = None,
        types: Sequence[SnapType] | None = None,
    ) -> list[SnapRecord]:
        raise NotImplementedError

    @abstractmethod
    async def set_status(
        self,
        *,
        business_id: str,
        snap_id: str,
        status: SnapStatus,
    ) -> SnapRecord:
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
