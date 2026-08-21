from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import uuid4

from .interface import SnapI
from .model import SnapModel, SnapRecord
from ..redis import RedisTransport


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

        business_id = self._validate_business_id(
            business_id,
        )

        record = SnapRecord(
            snap_id=str(
                uuid4(),
            ),
            business_id=business_id,
            snap=snap,
            status="active",
        )

        await self._redis.snap_set(
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

        business_id = self._validate_business_id(
            business_id,
        )

        snap_id = self._validate_snap_id(
            snap_id,
        )

        value = await self._redis.snap_get(
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

        business_id = self._validate_business_id(
            business_id,
        )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        keys = await self._redis.snap_keys(
            pattern=f"snap:{business_id}:*",
        )

        snaps: list[SnapRecord] = []

        for key in keys:

            if len(snaps) >= limit:
                break

            value = await self._redis.snap_get(
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

        business_id = self._validate_business_id(
            business_id,
        )

        snap_id = self._validate_snap_id(
            snap_id,
        )

        await self._redis.snap_delete(
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

        await self._redis.snap_set(
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

    # ==========================================================
    # Refresh
    # ==========================================================

    async def refresh(
        self,
        *,
        business_id: str,
        snap_id: str,
        ttl: timedelta | None = None,
    ) -> bool:

        business_id = self._validate_business_id(
            business_id,
        )

        snap_id = self._validate_snap_id(
            snap_id,
        )

        return await self._redis.snap_expire(
            key=self._build_key(
                business_id=business_id,
                snap_id=snap_id,
            ),
            ttl=ttl or self._DEFAULT_TTL,
        )

    # ==========================================================
    # Serialization
    # ==========================================================

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

    # ==========================================================
    # Key
    # ==========================================================

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

    # ==========================================================
    # Validation
    # ==========================================================

    @staticmethod
    def _validate_snap_id(
        snap_id: str,
    ) -> str:

        if not isinstance(
            snap_id,
            str,
        ):
            raise TypeError(
                "snap_id must be a string.",
            )

        snap_id = snap_id.strip()

        if not snap_id:
            raise ValueError(
                "snap_id cannot be empty.",
            )

        return snap_id

    @staticmethod
    def _validate_business_id(
        business_id: str,
    ) -> str:

        if not isinstance(
            business_id,
            str,
        ):
            raise TypeError(
                "business_id must be a string.",
            )

        business_id = business_id.strip()

        if not business_id:
            raise ValueError(
                "business_id cannot be empty.",
            )

        return business_id
