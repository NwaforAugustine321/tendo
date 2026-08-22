"""Snap feed service — tab resolution, ownership checks, status transitions."""

from __future__ import annotations

from typing import Any

from app.communication.ws.server import redis_transport
from app.lib.errors import NotFoundError, ValidationError
from app.runtime.agent_hub.snap.models import (
    SNAP_TABS,
    SnapRecord,
    SnapStatus,
    SnapTab,
)
from app.runtime.agent_hub.snap.persist_store import SnapPersistence
from app.runtime.agent_hub.snap.repository import SnapRepository
from app.runtime.agent_hub.snap.service import SnapService

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200

_repository: SnapRepository | None = None


def _get_repository() -> SnapRepository:
    global _repository
    if _repository is None:
        _repository = SnapRepository(
            service=SnapService(redis=redis_transport),
            persistence=SnapPersistence(),
        )
    return _repository


def _serialize(record: SnapRecord) -> dict[str, Any]:
    return {
        "snap_id": record.snap_id,
        "business_id": record.business_id,
        "type": record.snap.type,
        "priority": record.snap.priority,
        "confidence": record.snap.confidence,
        "title": record.snap.title,
        "message": record.snap.message,
        "why_it_matters": record.snap.why_it_matters,
        "action": record.snap.action,
        "domain": record.snap.domain,
        "status": record.status,
        "created_at": record.created_at,
    }


def _resolve_limit(limit: int | None) -> int:
    if limit is None:
        return _DEFAULT_LIMIT
    if limit <= 0:
        raise ValidationError("limit must be greater than zero.")
    return min(limit, _MAX_LIMIT)


def _validate_tab(tab: str) -> SnapTab:
    if tab not in SNAP_TABS:
        raise ValidationError(
            f"tab must be one of: {', '.join(SNAP_TABS)}.",
        )
    return tab  # type: ignore[return-value]


async def _authorize(business_id: str, user_id: str) -> str:
    """
    The Supabase client uses the service role key, so row level security is
    bypassed and ownership has to be enforced here.
    """

    business_id = business_id.strip()

    if not business_id:
        raise ValidationError("business_id is required.")

    owns = await _get_repository().owns_business(
        business_id=business_id,
        user_id=user_id,
    )

    if not owns:
        raise NotFoundError("Business not found")

    return business_id


async def list_snaps(
    *,
    business_id: str,
    user_id: str,
    tab: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:

    business_id = await _authorize(business_id, user_id)

    records = await _get_repository().list_tab(
        business_id=business_id,
        tab=_validate_tab(tab),
        limit=_resolve_limit(limit),
    )

    return [_serialize(record) for record in records]


async def set_snap_status(
    *,
    business_id: str,
    snap_id: str,
    user_id: str,
    status: SnapStatus,
) -> dict[str, Any]:

    business_id = await _authorize(business_id, user_id)

    snap_id = snap_id.strip()

    if not snap_id:
        raise ValidationError("snap_id is required.")

    try:
        record = await _get_repository().set_status(
            business_id=business_id,
            snap_id=snap_id,
            status=status,
        )
    except ValueError as exc:
        raise NotFoundError("Snap not found") from exc

    return _serialize(record)


async def save_snap(
    *,
    business_id: str,
    snap_id: str,
    user_id: str,
) -> dict[str, Any]:

    return await set_snap_status(
        business_id=business_id,
        snap_id=snap_id,
        user_id=user_id,
        status="pending",
    )


async def complete_snap(
    *,
    business_id: str,
    snap_id: str,
    user_id: str,
) -> dict[str, Any]:

    return await set_snap_status(
        business_id=business_id,
        snap_id=snap_id,
        user_id=user_id,
        status="completed",
    )
