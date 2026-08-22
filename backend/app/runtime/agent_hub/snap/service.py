from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from .interface import SnapI
from .models import (
    SnapModel,
    SnapRecord,
    SnapStatus,
    SnapType,
    sort_key,
)
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
            created_at=datetime.now(
                timezone.utc,
            ).isoformat(),
        )

        await self._write(
            record,
        )

        return record

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

    async def list(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> list[SnapRecord]:

        return await self.query(
            business_id=business_id,
            limit=limit,
        )

    async def get_active(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> list[SnapRecord]:

        return await self.query(
            business_id=business_id,
            limit=limit,
            statuses=("active",),
        )

    async def query(
        self,
        *,
        business_id: str,
        limit: int,
        statuses: Sequence[SnapStatus] | None = None,
        types: Sequence[SnapType] | None = None,
    ) -> list[SnapRecord]:
        """
        Filters are applied before `limit` so the cap counts matching Snaps
        rather than scanned keys. Redis SCAN returns keys in arbitrary order,
        so the full key set for the business is read before sorting. Volume is
        bounded by the Snap TTL.
        """

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        keys = await self._redis.keys(
            pattern=self._build_pattern(
                business_id=business_id,
            ),
        )

        matches: list[SnapRecord] = []

        for key in keys:

            value = await self._redis.get(
                key=key,
            )

            if value is None:
                continue

            record = self._deserialize(
                value,
            )

            if statuses and record.status not in statuses:
                continue

            if types and record.snap.type not in types:
                continue

            matches.append(
                record,
            )

        matches.sort(
            key=sort_key,
        )

        return matches[:limit]

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

        updated = replace(
            snap,
            status=status,
        )

        await self._write(
            updated,
        )

        return updated

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

        await self._redis.delete(
            key=self._build_key(
                business_id=business_id,
                snap_id=snap_id,
            ),
        )

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

    async def _write(
        self,
        record: SnapRecord,
    ) -> None:

        await self._redis.set(
            key=self._build_key(
                business_id=record.business_id,
                snap_id=record.snap_id,
            ),
            value=self._serialize(
                record,
            ),
            ttl=self._DEFAULT_TTL,
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
            domain=snap_data["domain"],
        )

        return SnapRecord(
            snap_id=value["snap_id"],
            business_id=value["business_id"],
            snap=snap,
            status=value.get(
                "status",
                "active",
            ),
            created_at=value.get(
                "created_at",
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
