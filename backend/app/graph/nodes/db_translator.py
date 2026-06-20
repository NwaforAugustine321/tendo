"""DB Translator node — converts raw DB results to natural language for MOA."""

import json
import logging

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def db_translator_node(state: GraphState) -> dict:
    """Convert db_result into a natural language summary for MOA to use."""
    db_result = state.get("db_result")

    if not db_result or not db_result.get("results"):
        return {"domain_result": {"summary": "No results."}}

    results = db_result["results"]
    event = state.get("event", {})
    user_message = event.get("text", "")

    parts = []
    for r in results:
        tool = r.get("tool", "unknown")
        if r.get("success"):
            data = r.get("data", {})
            parts.append(f"Tool '{tool}' succeeded: {json.dumps(data, default=str)[:500]}")
        else:
            error = r.get("error", "unknown error")
            parts.append(f"Tool '{tool}' failed: {error}")

    raw_context = "\n".join(parts)

    config = load("db_translator")
    llm = get_llm()

    prompt = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": f"User asked: {user_message}\n\nDB Results:\n{raw_context}"},
    ]

    try:
        response = await llm.ainvoke(prompt)
        summary = response.content.strip()
        logger.info(f"DB translator: {summary[:100]}")
    except Exception as e:
        logger.warning(f"DB translator LLM failed: {e}")
        summary = f"Operation completed: {len(results)} action(s) performed."

    return {"domain_result": {"summary": summary}}
