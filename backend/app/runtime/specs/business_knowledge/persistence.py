import json
import logging
from datetime import datetime, timezone

from app.business_knowledge.models import InsightOutput
from app.memory.memory import Memory

logger = logging.getLogger(__name__)


class InsightPersistence:
    def __init__(self, business_id: str):
        self._business_id = business_id
        self._memory = Memory(scopes=[f"/business/{business_id}"], business_id=business_id)

    async def persist(self, output: InsightOutput) -> int:
        if not output.insights:
            return 0

        stored = 0
        for entry in output.insights:
            timestamp = entry.timestamp or datetime.now(timezone.utc).isoformat()

            metadata = {
                "area": entry.area,
                "timestamp": timestamp,
                "payload": entry.payload,
            }

            try:
                await self._memory.remember(
                    content=entry.insight,
                    metadata=metadata,
                )
                stored += 1
            except Exception as e:
                logger.warning(f"Failed to persist insight: {e}")

        logger.info(f"InsightPersistence: stored {stored}/{len(output.insights)} insights")
        return stored
