from __future__ import annotations

from app.runtime.agents.run_context import RunContext

from .retrieval import RetrievalEngine


class DefaultRetrieval(
    RetrievalEngine,
):
    """
    Default retrieval strategy.

    Builds a search query from the current
    user request.
    """

    async def build_query(
        self,
        ctx: RunContext,
    ) -> str:

        return ctx.user_request.strip()
