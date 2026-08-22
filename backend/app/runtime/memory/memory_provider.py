from __future__ import annotations

import logging

from app.runtime.agents.run_context import RunContext
from app.runtime.conversation.context import ConversationContext
from app.runtime.context_manager.optimizers.default_optimizer import (
    DefaultConversationOptimizer,
)
from app.runtime.context_manager.optimizers.optimizer import (
    ContextOptimizer as Optimizer,
    OptimizationResult,
)

from .context import MemoryContext
from .reflection import MemoryReflectionEngine
from .store import MemoryStore


logger = logging.getLogger(__name__)


HISTORY_MESSAGES = 8

HISTORY_MESSAGE_CHARS = 500


REWRITE_QUERY_PROMPT = """
Convert the current task into one concise semantic search query.

The query must describe the information that should be retrieved
from memory.

Use the available context to resolve references, names, entities,
dates, identifiers, and other details when relevant.

Preserve the intent of the task.

Do not answer the task.
Do not analyze the information.
Do not generate signals.
Do not classify the information.
Do not return JSON.
Do not return an array.
Do not return an empty result.

Always return a non-empty plain-text retrieval query.

Keep the query under 150 characters.

<task>
{task}
<task>

Return only the retrieval query.

"""

# <Context>
# {context}
# </Context>


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
        reflection: MemoryReflectionEngine | None = None,
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

    async def build_query(
        self,
        ctx: RunContext,
    ) -> str:
        """
        Build the memory retrieval query from the current run.
        """

        return await self._rewrite_query(ctx)

    def _run_context(
        self,
        ctx: RunContext,
    ) -> str:
        """
        Messages from the current run, as a context block.
        """

        lines: list[str] = []

        for message in ctx.messages[-HISTORY_MESSAGES:]:

            if not message.content:
                continue

            role = str(
                getattr(
                    message.role,
                    "value",
                    message.role,
                ),
            )

            if role not in ("user", "assistant"):
                continue

            content = message.content

            if not isinstance(content, str):
                content = str(content)

            content = content.strip()

            if len(content) > HISTORY_MESSAGE_CHARS:
                content = (
                    content[:HISTORY_MESSAGE_CHARS] + "..."
                )

            lines.append(
                f"<{role}>: {content}",
            )

        return "\n".join(lines)

    async def _rewrite_query(
        self,
        ctx: RunContext,
    ) -> str:
        """
        Rewrite a query into focused memory search phrases.
        """

        query = (ctx.user_request or "").strip()

        if not query:
            return ""

        llm = ctx.session._agent._llm

        model = (
            getattr(llm, "base_model", None)
            or getattr(llm, "model", None)
        )

        if model is None:
            return query

        messages = [
            {
                "role": "system",
                "content": REWRITE_QUERY_PROMPT.replace(
                    "{task}", query
                )

            }
        ]

        try:
            response = await model.ainvoke(
                messages,
            )

            content = getattr(
                response,
                "content",
                str(response),
            )

            if isinstance(
                content,
                list,
            ):
                content = "".join(
                    str(part)
                    for part in content
                )

            rewritten = str(
                content,
            ).strip()

            return rewritten if rewritten else query

        except Exception:
            logger.debug(
                "Memory query rewrite skipped.",
                exc_info=True,
            )
            return query

    async def retrieve(
        self,
        ctx: RunContext,
        query: str | None = None,
    ) -> MemoryContext:
        """
        Retrieve relevant memories.
        """

        if query is None:
            query = await self.build_query(
                ctx,
            )

        query = query.strip()

        if not query:
            return MemoryContext()

        return await self._store.retrieve(
            query=query,
            limit=5,
        )

    async def reflect(
        self,
        ctx: RunContext,
    ) -> None:

        if not self._reflection:
            return

        reflection = await self._reflection.reflect(
            ctx,
        )

        if reflection.empty:
            return

        await self._store.save(
            reflection=reflection,
        )
