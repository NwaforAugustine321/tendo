from __future__ import annotations

from app.runtime.agents.run_context import RunContext

from .retrieval import RetrievalEngine


class DefaultRetrieval(
    RetrievalEngine,
):
    """
    Default retrieval strategy.

    Builds a search query from the current
    user request, rewriting it into focused
    search phrases for better semantic retrieval.
    """

    async def build_query(
        self,
        ctx: RunContext,
    ) -> str:

        raw_query = ctx.user_request.strip()

        if not raw_query:
            return ""

        return await self._rewrite_query(raw_query)

    async def _rewrite_query(
        self,
        query: str,
    ) -> str:
        """
        Use a small LLM call to rewrite the user query
        into focused search phrases for RAG retrieval.
        """

        from app.llm.client import get_client

        llm = get_client()

        messages = [
            {
                "role": "system",
                "content": (
                    "Rewrite the following user message into 1-3 short, "
                    "focused search phrases for retrieving relevant documents. "
                    "Extract the key concepts, entities, and intent. "
                    "Output only the search phrases, one per line. "
                    "No explanation."
                ),
            },
            {
                "role": "user",
                "content": query,
            },
        ]

        try:
            response = await llm.ainvoke(messages)
            content = getattr(response, "content", str(response))
            if isinstance(content, list):
                content = "".join(str(p) for p in content)
            rewritten = str(content).strip()
            return rewritten if rewritten else query
        except Exception:
            return query
