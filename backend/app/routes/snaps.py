"""Snap feed routes — thin HTTP layer."""

from fastapi import APIRouter, Depends, Query

from app.lib.auth_dependency import get_current_user
from app.services.snap import (
    complete_snap,
    list_snaps,
    save_snap,
)

router = APIRouter(prefix="/snaps", tags=["snaps"])


@router.get("/{business_id}")
async def list_snaps_route(
    business_id: str,
    tab: str = Query("attention"),
    limit: int | None = Query(None, ge=1),
    user: dict = Depends(get_current_user),
):
    """Return live Snaps for a tab: attention, recommendation, or priority."""
    snaps = await list_snaps(
        business_id=business_id,
        user_id=user["user_id"],
        tab=tab,
        limit=limit,
    )
    return {"snaps": snaps, "tab": tab, "count": len(snaps)}


@router.post("/{business_id}/{snap_id}/save")
async def save_snap_route(
    business_id: str,
    snap_id: str,
    user: dict = Depends(get_current_user),
):
    """Save a Snap, moving it to the priority tab."""
    snap = await save_snap(
        business_id=business_id,
        snap_id=snap_id,
        user_id=user["user_id"],
    )
    return {"snap": snap}


@router.post("/{business_id}/{snap_id}/complete")
async def complete_snap_route(
    business_id: str,
    snap_id: str,
    user: dict = Depends(get_current_user),
):
    """Mark a Snap completed, removing it from all tabs."""
    snap = await complete_snap(
        business_id=business_id,
        snap_id=snap_id,
        user_id=user["user_id"],
    )
    return {"snap": snap}
