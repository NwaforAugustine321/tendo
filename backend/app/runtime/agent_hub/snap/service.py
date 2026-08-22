from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import uuid4

from .interface import SnapI
from .models import SnapModel, SnapRecord
from app.communication.transports.redis import RedisTransport


class SnapService(
    SnapI,
):

    _DEFAULT_TTL = timedelta(
        hours=24,
    )

    def __init__(
        self,
        redis: RedisTransport,
    ) -> None:

        self._redis = redis

    # ==========================================================
    # Create
    # ==========================================================

    async def create(
        self,
        *,
        business_id: str,
        snap: SnapModel,
    ) -> SnapRecord:

        record = SnapRecord(
            snap_id=str(
                uuid4(),
            ),
            business_id=business_id,
            snap=snap,
            status="active",
        )

        await self._redis.set(
            key=self._build_key(
                business_id=business_id,
                snap_id=record.snap_id,
            ),
            value=self._serialize(
                record,
            ),
            ttl=self._DEFAULT_TTL,
        )

        return record

    # ==========================================================
    # Get
    # ==========================================================

    async def get(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord | None:

        value = await self._redis.get(
            key=self._build_key(
                business_id=business_id,
                snap_id=snap_id,
            ),
        )

        if value is None:
            return None

        return self._deserialize(
            value,
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

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        keys = await self._redis.keys(
            pattern=self._build_pattern(
                business_id=business_id,
            ),
        )

        snaps: list[SnapRecord] = []

        for key in keys:

            if len(snaps) >= limit:
                break

            value = await self._redis.get(
                key=key,
            )

            if value is None:
                continue

            snaps.append(
                self._deserialize(
                    value,
                ),
            )

        return snaps

    # ==========================================================
    # Get Active
    # ==========================================================

    async def get_active(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> list[SnapRecord]:

        snaps = await self.list(
            business_id=business_id,
            limit=limit,
        )

        return [
            snap
            for snap in snaps
            if snap.status == "active"
        ]

    # ==========================================================
    # Delete
    # ==========================================================

    async def delete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> None:

        await self._redis.delete(
            key=self._build_key(
                business_id=business_id,
                snap_id=snap_id,
            ),
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

        completed = SnapRecord(
            snap_id=snap.snap_id,
            business_id=snap.business_id,
            snap=snap.snap,
            status="completed",
        )

        await self._redis.set(
            key=self._build_key(
                business_id=business_id,
                snap_id=snap_id,
            ),
            value=self._serialize(
                completed,
            ),
            ttl=self._DEFAULT_TTL,
        )

        return completed

    async def refresh(
        self,
        *,
        business_id: str,
        snap_id: str,
        ttl: timedelta | None = None,
    ) -> bool:

        return await self._redis.expire(
            key=self._build_key(
                business_id=business_id,
                snap_id=snap_id,
            ),
            ttl=ttl or self._DEFAULT_TTL,
        )

    @staticmethod
    def _serialize(
        snap: SnapRecord,
    ) -> dict[str, Any]:

        return asdict(
            snap,
        )

    @staticmethod
    def _deserialize(
        value: dict[str, Any],
    ) -> SnapRecord:

        snap_data = value["snap"]

        snap = SnapModel(
            type=snap_data["type"],
            priority=snap_data["priority"],
            confidence=float(
                snap_data["confidence"],
            ),
            title=snap_data["title"],
            message=snap_data["message"],
            why_it_matters=snap_data["why_it_matters"],
            action=snap_data["action"],
        )

        return SnapRecord(
            snap_id=value["snap_id"],
            business_id=value["business_id"],
            snap=snap,
            status=value.get(
                "status",
                "active",
            ),
        )

    @staticmethod
    def _build_key(
        *,
        business_id: str,
        snap_id: str,
    ) -> str:

        return (
            f"snap:"
            f"{business_id}:"
            f"{snap_id}"
        )

    @staticmethod
    def _build_pattern(
        *,
        business_id: str,
    ) -> str:

        return (
            f"snap:"
            f"{business_id}:"
            "*"
        )
