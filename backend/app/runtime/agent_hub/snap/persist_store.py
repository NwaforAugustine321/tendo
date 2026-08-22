from __future__ import annotations

from typing import Any

from .models import SnapModel, SnapRecord
from .repository import SnapPersistenceI

from app.db.client import get_client


class SnapPersistence(
    SnapPersistenceI,
):

    _TABLE = "snaps"
    _BUSINESS_TABLE = "business_profiles"

    def __init__(self) -> None:
        self._db = get_client()

    async def save(
        self,
        *,
        snap: SnapRecord,
    ) -> SnapRecord:

        payload = self._serialize(
            snap,
        )

        response = (
            self._db
            .table(self._TABLE)
            .upsert(
                payload,
                on_conflict="business_id,snap_id",
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to persist Snap.",
            )

        return self._deserialize(
            response.data[0],
        )

    async def get(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> SnapRecord | None:

        response = (
            self._db
            .table(self._TABLE)
            .select("*")
            .eq(
                "business_id",
                business_id,
            )
            .eq(
                "snap_id",
                snap_id,
            )
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._deserialize(
            response.data[0],
        )

    async def fetch_business_ids(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[str]:

        if offset < 0:
            raise ValueError(
                "offset cannot be negative.",
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        response = (
            self._db
            .table(
                self._BUSINESS_TABLE,
            )
            .select(
                "id",
            )
            .order(
                "id",
                desc=False,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return [
            str(
                row["id"],
            )
            for row in (
                response.data or []
            )
            if row.get("id") is not None
        ]

    async def delete(
        self,
        *,
        business_id: str,
        snap_id: str,
    ) -> None:

        (
            self._db
            .table(self._TABLE)
            .delete()
            .eq(
                "business_id",
                business_id,
            )
            .eq(
                "snap_id",
                snap_id,
            )
            .execute()
        )

    @staticmethod
    def _serialize(
        snap: SnapRecord,
    ) -> dict[str, Any]:

        return {
            "snap_id": snap.snap_id,
            "business_id": snap.business_id,
            "type": snap.snap.type,
            "priority": snap.snap.priority,
            "confidence": snap.snap.confidence,
            "title": snap.snap.title,
            "message": snap.snap.message,
            "why_it_matters": snap.snap.why_it_matters,
            "action": snap.snap.action,
            "domain": snap.snap.domain,
            "status": snap.status,
        }

    @staticmethod
    def _deserialize(
        value: dict[str, Any],
    ) -> SnapRecord:

        snap = SnapModel(
            type=value["type"],
            priority=value["priority"],
            confidence=float(
                value["confidence"],
            ),
            title=value["title"],
            message=value["message"],
            why_it_matters=value["why_it_matters"],
            action=value["action"],
            domain=value["domain"],
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
