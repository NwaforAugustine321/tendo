import logging

logger = logging.getLogger(__name__)


async def rewrite_query(task_prompt: str) -> str:
    from app.llm.client import get_client
    from app.lib.i18n import _get_i18n

    try:
        i18n = _get_i18n()
        rewriter_prompt = i18n.get("slices.knowledge_search_query_system_prompt")
        query_template = i18n.get("slices.knowledge_search_query")
        query = query_template.format(task_prompt=task_prompt)

        llm = get_client()
        messages = [
            {"role": "system", "content": rewriter_prompt},
            {"role": "user", "content": query},
        ]
        response = await llm.ainvoke(messages)
        search_query = response.content.strip() if response.content else task_prompt

        return search_query if search_query else task_prompt

    except Exception as e:
        logger.warning(f"Query rewriting failed: {e}")
        return task_prompt
