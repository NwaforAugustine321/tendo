from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import replace
from datetime import timedelta

from .interface import SnapI
from .models import (
    SnapModel,
    SnapRecord,
    SnapStatus,
    SnapTab,
    SnapType,
    resolve_tab,
)


class SnapPersistenceI(ABC):
    """
    Durable persistence boundary for saved Snaps.
    """

    @abstractmethod
    async def save(
        self,
        *,
        snap: SnapRecord,
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
    ) -> SnapRecord | None:
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
    async def fetch_business_ids(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def owns_business(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> bool:
        raise NotImplementedError


class SnapRepository(
    SnapI,
):
    """
    Redis holds the live feed of active Snaps and expires them on a TTL.
    The `snaps` table owns Snaps the user has saved, which must outlive that
    TTL. Status changes write the table first and then mirror into Redis so
    the live feed agrees with durable state while the key is still present.
    """

    def __init__(
        self,
        *,
        service: SnapI,
        persistence: SnapPersistenceI,
    ) -> None:

        self._service = service
        self._persistence = persistence

    async def create(
        self,
        *,
        business_id: str,
        snap: SnapModel,
    ) -> SnapRecord:

        return await self._service.create(
            business_id=business_id,
            snap=snap,
        )

    async def get(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord | None:

        snap = await self._service.get(
            business_id=business_id,
            snap_id=snap_id,
        )

        if snap is not None:
            return snap

        return await self._persistence.get(
            business_id=business_id,
            snap_id=snap_id,
        )

    async def list(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> list[SnapRecord]:

        return await self._service.list(
            business_id=business_id,
            limit=limit,
        )

    async def get_active(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> list[SnapRecord]:

        return await self._service.get_active(
            business_id=business_id,
            limit=limit,
        )

    async def query(
        self,
        *,
        business_id: str,
        limit: int,
        statuses: Sequence[SnapStatus] | None = None,
        types: Sequence[SnapType] | None = None,
    ) -> list[SnapRecord]:

        return await self._service.query(
            business_id=business_id,
            limit=limit,
            statuses=statuses,
            types=types,
        )

    async def list_tab(
        self,
        *,
        business_id: str,
        tab: SnapTab,
        limit: int,
    ) -> list[SnapRecord]:

        tab_filter = resolve_tab(
            tab,
        )

        source: SnapI | SnapPersistenceI = (
            self._persistence
            if tab == "priority"
            else self._service
        )

        return await source.query(
            business_id=business_id,
            limit=limit,
            statuses=tab_filter.statuses,
            types=tab_filter.types,
        )

    async def set_status(
        self,
        *,
        business_id: str,
        snap_id: str,
        status: SnapStatus,
    ) -> SnapRecord:

        snap = await self.get(
            business_id=business_id,
            snap_id=snap_id,
        )

        if snap is None:
            raise ValueError(
                f"Snap '{snap_id}' was not found.",
            )

        updated = await self._persistence.set_status(
            business_id=business_id,
            snap_id=snap_id,
            status=status,
        )

        if updated is None:
            updated = await self._persistence.save(
                snap=replace(
                    snap,
                    status=status,
                ),
            )

        live = await self._service.get(
            business_id=business_id,
            snap_id=snap_id,
        )

        if live is not None:
            await self._service.set_status(
                business_id=business_id,
                snap_id=snap_id,
                status=status,
            )

        return updated

    async def save(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord:

        return await self.set_status(
            business_id=business_id,
            snap_id=snap_id,
            status="pending",
        )

    async def complete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord:

        return await self.set_status(
            business_id=business_id,
            snap_id=snap_id,
            status="completed",
        )

    async def delete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> None:

        await self._service.delete(
            business_id=business_id,
            snap_id=snap_id,
        )

        await self._persistence.delete(
            business_id=business_id,
            snap_id=snap_id,
        )

    async def refresh(
        self,
        *,
        business_id: str,
        snap_id: str,
        ttl: timedelta | None = None,
    ) -> bool:

        return await self._service.refresh(
            business_id=business_id,
            snap_id=snap_id,
            ttl=ttl,
        )

    async def fetch_business_ids(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[str]:

        if offset < 0:
            raise ValueError(
                "offset must be greater than or equal to zero.",
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        return await self._persistence.fetch_business_ids(
            offset=offset,
            limit=limit,
        )

    async def owns_business(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> bool:

        return await self._persistence.owns_business(
            business_id=business_id,
            user_id=user_id,
        )
