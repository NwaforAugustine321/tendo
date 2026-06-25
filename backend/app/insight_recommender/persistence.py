import logging

from app.db.tools.business_insight import store_business_insight

logger = logging.getLogger(__name__)


async def persist_insights(insights: list[str], business_id: str, source_agent: str) -> int:
    stored = 0
    for text in insights:
        if not text or not text.strip():
            continue
        try:
            await store_business_insight(business_id, text, source_agent)
            stored += 1
        except Exception as e:
            logger.warning(f"Failed to persist insight: {e}")

    logger.info(f"Persisted {stored}/{len(insights)} insights for {business_id}")
    return stored
