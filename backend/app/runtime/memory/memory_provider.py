from __future__ import annotations

from app.runtime.agents.run_context import RunContext

from .context import MemoryContext
from .reflection import MemoryReflectionEngine
from .store import MemoryStore
from app.runtime.context_manager.optimizers.optimizer import (
    ContextOptimizer as Optimizer,
    OptimizationResult,
)
from app.runtime.context_manager.optimizers.default_optimizer import (
    DefaultConversationOptimizer,
)


class MemoryProvider:
    """
    Coordinates long-term memory.

    Responsibilities
    ----------------
    - Retrieve memories.
    - Reflect over completed runs.
    - Persist learned memories.
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        reflection: MemoryReflectionEngine,
        optimizer: Optimizer | None = None,
    ) -> None:

        self._store = store
        self._reflection = reflection

        self._optimizer = (
            optimizer
            or DefaultConversationOptimizer(
                provider=self,
            )
        )

    @property
    def store(
        self,
    ) -> MemoryStore:

        return self._store

    @property
    def reflection(
        self,
    ) -> MemoryReflectionEngine:

        return self._reflection

    async def optimize(
        self,
        *,
        conversation: ConversationContext,
        current_tokens: int,
        target_tokens: int,
    ) -> OptimizationResult:

        return await self._optimizer.optimize(
            conversation=conversation,
            current_tokens=current_tokens,
            target_tokens=target_tokens,
        )

    def middleware(
        self,
    ) -> list:

        return []

    def build_query(
        self,
        ctx: RunContext,
    ) -> str:
        """
        Build the memory retrieval query from user request.
        """

        return ctx.user_request.strip()

    async def _rewrite_query(
        self,
        query: str,
    ) -> str:
        """
        Use a small LLM call to rewrite the user query
        into a better search phrase for memory retrieval.
        """

        from app.llm.client import get_client

        llm = get_client()

        messages = [
            {
                "role": "system",
                "content": (
                    "Rewrite the following user message into 1-3 short, "
                    "focused search phrases for retrieving relevant memories. "
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

    async def retrieve(
        self,
        ctx: RunContext,
    ) -> MemoryContext:

        query = self.build_query(
            ctx,
        )

        if not query:
            return MemoryContext()

        # Rewrite query for better semantic search.
        # rewritten = await self._rewrite_query(query)

        return await self.store.retrieve(
            query=query,
            limit=5,
        )

    async def reflect(
        self,
        ctx: RunContext,
    ) -> None:

        reflection = await self.reflection.reflect(
            ctx,
        )

        if reflection.empty:
            return

        await self.store.save(
            reflection=reflection,
        )
