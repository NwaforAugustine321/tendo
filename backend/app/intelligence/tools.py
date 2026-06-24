import json
import logging

from langchain_core.tools import tool

from app.lib.i18n import _get_i18n
from app.memory.memory import Memory

logger = logging.getLogger(__name__)


def _get_insight_memory(business_id: str) -> Memory:
    return Memory(scope=f"/insights/{business_id}")


def _slice(key: str) -> str:
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")


async def _rewrite_query(query: str, insight: str, business_id: str) -> str:
    try:
        from app.llm.client import get_client

        llm = get_client()
        system_prompt = _slice("knowledge_search_query_system_prompt")
        query_template = _slice("knowledge_search_query")
        combined = f"business_id: {business_id}\nquery: {query}\ninsight: {insight}"
        formatted = query_template.format(task_prompt=combined)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted},
        ]

        response = await llm.ainvoke(messages)
        rewritten = response.content.strip() if response.content else query or insight
        return rewritten if rewritten else query or insight
    except Exception as e:
        logger.warning(f"Query rewrite failed: {e}")
        return query or insight


@tool
async def search_insights(
    query: str = "", insight: str = "", business_id: str = "", limit: int = 5
) -> str:
    """Search existing business insights by semantic similarity. Provide a query and/or insight text. Uses LLM to rewrite into an optimized search query."""
    try:
        memory = _get_insight_memory(business_id)
        search_query = await _rewrite_query(query, insight, business_id)

        matches = await memory.recall(
            query=search_query,
            limit=limit,
        )

        if not matches:
            return json.dumps({"matches": [], "count": 0})

        results = []
        for m in matches:
            results.append({
                "insight": m.record.content,
                "metadata": m.record.metadata,
                "score": m.score,
                "importance": m.record.importance,
                "created_at": m.record.created_at.isoformat() if m.record.created_at else "",
            })

        return json.dumps({"matches": results, "count": len(results)}, default=str)
    except Exception as e:
        logger.warning(f"search_insights failed: {e}")
        return json.dumps({"matches": [], "count": 0, "note": "No existing insights found"})


INTELLIGENCE_TOOLS = [search_insights]
