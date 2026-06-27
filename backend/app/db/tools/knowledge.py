import json
import logging

from langchain_core.tools import tool

from app.memory.memory import Memory

logger = logging.getLogger(__name__)


@tool
async def search_business_knowledge(query: str = "", business_id: str = "", limit: int = 10) -> str:
    """Search business-level knowledge and insights by semantic similarity. Always use this first to understand business context."""
    try:
        memory = Memory(scope=f"/insights/{business_id}")
        results = await memory.recall(query=query, limit=limit)
        entries = [{"summary": m.record.content} for m in results]
        return json.dumps(entries, default=str)
    except Exception as e:
        logger.warning(f"search_business_knowledge failed: {e}")
        return json.dumps([])
