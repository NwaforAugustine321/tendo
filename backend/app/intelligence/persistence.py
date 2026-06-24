import json
import logging
from datetime import datetime, timezone

from app.intelligence.models import InsightOutput
from app.memory.memory import Memory

logger = logging.getLogger(__name__)


class InsightPersistence:
    def __init__(self, business_id: str):
        self._business_id = business_id
        self._memory = Memory(scope=f"/insights/{business_id}")

    async def persist(self, output: InsightOutput) -> int:
        if not output.insights:
            return 0

        stored = 0
        for entry in output.insights:
            timestamp = entry.timestamp or datetime.now(timezone.utc).isoformat()

            metadata = {
                "area": entry.area,
                "timestamp": timestamp,
                "payload": json.dumps(entry.payload, default=str),
            }

            entities = entry.payload.get("entities", [])
            categories = [entry.area]
            if isinstance(entities, list):
                categories.extend(entities[:5])

            try:
                await self._memory.remember(
                    content=entry.insight,
                    scope=entry.area,
                    categories=categories,
                    metadata=metadata,
                    importance=entry.importance,
                    source="bla",
                )
                stored += 1
            except Exception as e:
                logger.warning(f"Failed to persist insight: {e}")

        logger.info(f"InsightPersistence: stored {stored}/{len(output.insights)} insights")
        return stored
