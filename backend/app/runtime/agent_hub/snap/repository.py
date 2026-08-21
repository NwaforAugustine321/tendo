from __future__ import annotations

from abc import ABC, abstractmethod

from .interface import SnapI
from .model import SnapModel, SnapRecord


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
    async def delete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> None:
        raise NotImplementedError


class SnapRepository(
    SnapI,
):

    def __init__(
        self,
        *,
        service: SnapI,
        persistence: SnapPersistenceI,
    ) -> None:

        self._service = service
        self._persistence = persistence

    # ==========================================================
    # Create
    # ==========================================================

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

    # ==========================================================
    # Get
    # ==========================================================

    async def get(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord | None:

        # Redis is the first source because it contains
        # currently live Snaps.
        snap = await self._service.get(
            business_id=business_id,
            snap_id=snap_id,
        )

        if snap is not None:
            return snap

        # Redis may have expired the Snap.
        #
        # A previously saved Snap can still exist in
        # durable persistence.
        return await self._persistence.get(
            business_id=business_id,
            snap_id=snap_id,
        )

    # ==========================================================
    # List
    # ==========================================================

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

    # ==========================================================
    # Active
    # ==========================================================

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

    # ==========================================================
    # Complete
    # ==========================================================

    async def complete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord:

        snap = await self.get(
            business_id=business_id,
            snap_id=snap_id,
        )

        if snap is None:
            raise ValueError(
                f"Snap '{snap_id}' was not found.",
            )

        # If the Snap is currently live in Redis,
        # let the service update its ephemeral state.
        live_snap = await self._service.get(
            business_id=business_id,
            snap_id=snap_id,
        )

        if live_snap is not None:
            return await self._service.complete(
                business_id=business_id,
                snap_id=snap_id,
            )

        # If Redis has expired but the Snap exists in
        # durable persistence, update the durable record.
        completed = SnapRecord(
            snap_id=snap.snap_id,
            business_id=snap.business_id,
            snap=snap.snap,
            status="completed",
        )

        return await self._persistence.save(
            snap=completed,
        )

    # ==========================================================
    # Save
    # ==========================================================

    async def save(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord:

        snap = await self._service.get(
            business_id=business_id,
            snap_id=snap_id,
        )

        if snap is None:
            # It may already have expired from Redis.
            # Check durable persistence as a fallback.
            snap = await self._persistence.get(
                business_id=business_id,
                snap_id=snap_id,
            )

        if snap is None:
            raise ValueError(
                f"Snap '{snap_id}' was not found.",
            )

        # Promote the Snap into durable persistence.
        saved = await self._persistence.save(
            snap=snap,
        )

        # Remove the ephemeral Redis copy after the durable
        # write succeeds.
        await self._service.delete(
            business_id=business_id,
            snap_id=snap_id,
        )

        return saved

    # ==========================================================
    # Delete
    # ==========================================================

    async def delete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> None:

        # Remove the live Redis copy.
        await self._service.delete(
            business_id=business_id,
            snap_id=snap_id,
        )

        # Also remove any durable copy.
        await self._persistence.delete(
            business_id=business_id,
            snap_id=snap_id,
        )
