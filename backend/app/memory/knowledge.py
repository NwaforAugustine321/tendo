import logging
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings

logger = logging.getLogger(__name__)

from langchain_core.tools import tool
from app.memory.memory import Memory


@tool
async def search_business_knowledge(query: str = "", business_id: str = "", limit: int = 30) -> str:
    """Search the business general knowledge. this give overview of the business context understanding"""
    import json as _json
    try:
        memory = Memory(scope=f"/insights/{business_id}")
        results = await memory.recall(query=query, limit=limit)
        entries = [{"summary": m.record.content} for m in results]
        return _json.dumps(entries, default=str)
    except Exception as e:
        logger.warning(f"search_business_knowledge failed: {e}")
        return _json.dumps([])


BUSINESS_KNOWLEDGE_TOOLS = [search_business_knowledge]