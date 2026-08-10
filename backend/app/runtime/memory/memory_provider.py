from __future__ import annotations

from app.runtime.agents.run_context import RunContext

from .context import MemoryContext
from .reflection import MemoryReflectionEngine
from .store import MemoryStore


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
    ) -> None:

        self._store = store
        self._reflection = reflection

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

    def middleware(
        self,
    ) -> list:

        return []

    def build_query(
        self,
        ctx: RunContext,
    ) -> str:
        """
        Build the memory retrieval query.
        """

        return ctx.user_request.strip()

    async def retrieve(
        self,
        ctx: RunContext,
    ) -> MemoryContext:

        query = self.build_query(
            ctx,
        )

        if not query:
            return MemoryContext()

        return await self.store.retrieve(
            query=query,
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
