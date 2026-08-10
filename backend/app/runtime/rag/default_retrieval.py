from __future__ import annotations

from app.runtime.agents.run_context import RunContext

from .retrieval import RetrievalEngine


class DefaultRetrieval(
    RetrievalEngine,
):
    """
    Default retrieval strategy.

    Builds a search query from the messages generated
    during the current run.
    """

    async def build_query(
        self,
        ctx: RunContext,
    ) -> str:

        return "\n".join(
            str(message.content)
            for message in ctx.current_messages
            if message.content
            and str(message.content).strip()
        )
