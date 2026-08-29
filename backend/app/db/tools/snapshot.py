"""Business Snapshot DB access — Supabase read/write."""

import logging

from app.db.client import get_client

logger = logging.getLogger(__name__)

TABLE_NAME = "business_snapshots"
BUSINESS_PROFILES_TABLE = "business_profiles"


def save_snapshot(snapshot_data: dict) -> dict:
    """Upsert a snapshot into business_snapshots (replaces existing for business_id).

    Args:
        snapshot_data: Dict with keys: id, business_id, generated_at,
            knowledge_version, stories, recommendations.
    """
    client = get_client()
    result = (
        client.table(TABLE_NAME)
        .upsert(snapshot_data, on_conflict="business_id")
        .execute()
    )
    return result.data[0] if result.data else snapshot_data


def get_latest_snapshot(business_id: str) -> dict | None:
    """Fetch the active snapshot row for a business.

    Returns the raw row dict or None if no snapshot exists.
    """
    client = get_client()
    try:
        result = (
            client.table(TABLE_NAME)
            .select("*")
            .eq("business_id", business_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None
    except Exception:
        return None



def get_active_business_ids() -> list[str]:
    """Query Supabase for all active business profile IDs."""
    client = get_client()
    result = (
        client.table("business_profiles")
        .select("id")
        .eq("onboarding_completed", True)
        .execute()
    )
    return [row["id"] for row in (result.data or [])]
