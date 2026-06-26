import json
import logging

from langchain_core.tools import tool

from app.memory.memory import Memory

logger = logging.getLogger(__name__)


def _get_insight_memory(business_id: str) -> Memory:
    return Memory(scope=f"/insights/{business_id}")


async def _rewrite_query(query: str, insight: str, business_id: str) -> str:
    from app.lib.query_rewriter import rewrite_query

    combined = f"business_id: {business_id}\nquery: {query}\ninsight: {insight}"
    return await rewrite_query(combined)


@tool
async def search_insights(
    query: str = "", insight: str = "", business_id: str = "", limit: int = 5
) -> str:
    """Search existing business insights by semantic similarity."""
    try:
        memory = _get_insight_memory(business_id)
        search_query = await _rewrite_query(query, insight, business_id)

        matches = await memory.recall(query=search_query, limit=limit)

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
        return json.dumps({"matches": [], "count": 0})


BUSINESS_KNOWLEDGE_TOOLS = [search_insights]
