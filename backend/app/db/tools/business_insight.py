import logging
from datetime import datetime, timezone

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def store_business_insight(business_id: str, insight: str, source_agent: str = "") -> dict:
    client = get_client()
    data = {
        "business_id": business_id,
        "insight": insight,
        "source_agent": source_agent,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = client.table("business_insights").insert(data).execute()
    return result.data[0] if result.data else data


async def get_business_insights(business_id: str, limit: int = 20) -> list[dict]:
    client = get_client()
    result = (
        client.table("business_insights")
        .select("*")
        .eq("business_id", business_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
