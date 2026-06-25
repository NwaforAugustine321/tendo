import logging
from datetime import datetime, timezone

from app.db.client import get_client

logger = logging.getLogger(__name__)

def get_business_understanding(business_id: str, confidence_threshold: float = 0.0) -> dict:
    """Retrieve business understanding hypotheses above confidence threshold."""
    # TODO: implement via app.db.client
    return {"understandings": []}


def add_evidence(
    business_id: str,
    understanding_id: str,
    evidence_type: str,
    source_reference: dict,
    description: str,
) -> dict:
    """Add evidence observation to an understanding."""
    # TODO: implement
    return {"status": "added"}


def update_confidence(business_id: str, understanding_id: str, new_confidence: float, reason: str) -> dict:
    """Update confidence score for an understanding."""
    # TODO: implement
    return {"status": "updated", "confidence": new_confidence}


def evolve_understanding(business_id: str, action: str, data: dict) -> dict:
    """Create, merge, or retire business hypotheses."""
    # TODO: implement
    return {"status": action, "data": data}


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
