"""Record knowledge tools — LangChain tool wrappers for record knowledge search."""

import json
import logging

from langchain_core.tools import tool

from app.memory.memory import Memory

logger = logging.getLogger(__name__)


def get_record_knowledge_tools(business_id: str, record_id: str) -> list:
    """Create record-scoped knowledge search tools.

    Returns tools that search within a specific record's knowledge store
    and the business-level knowledge store.
    """
    from app.record_knowledge.store import _get_storage

    @tool
    async def search_record_knowledge(query: str = "", limit: int = 10) -> str:
        """Search knowledge stored for this record by semantic similarity."""
        try:
            memory = Memory(scope=f"/{business_id}/{record_id}", storage=_get_storage())
            results = await memory.recall(query=query, limit=limit)
            entries = [{"summary": m.record.content, "type": (m.record.metadata or {}).get("content_type", "")} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_record_knowledge failed: {e}")
            return json.dumps([])

    @tool
    async def search_business_knowledge(query: str = "", limit: int = 10) -> str:
        """Search business-level knowledge. Always use this first to understand business context of what already happened in the business."""
        try:
            memory = Memory(scope=f"/insights/{business_id}")
            results = await memory.recall(query=query, limit=limit)
            entries = [{"summary": m.record.content} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_business_knowledge failed: {e}")
            return json.dumps([])

    return [search_record_knowledge, search_business_knowledge]
