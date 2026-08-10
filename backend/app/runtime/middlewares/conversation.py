from __future__ import annotations

from app.runtime.middlewares.middleware import (
    AgentMiddleware,
    AfterLLMEvent,
    AfterToolsEvent,
)
from app.runtime.agents.run_context import (
    RunContext,
)
from app.runtime.conversation.provider import (
    ConversationProvider,
)


class ConversationMiddleware(
    AgentMiddleware,
):
    """
    Synchronizes the in-memory conversation with the
    persistent conversation store.
    """

    def __init__(
        self,
        *,
        provider: ConversationProvider,
    ) -> None:

        self._provider = provider

    @property
    def provider(
        self,
    ) -> ConversationProvider:

        return self._provider

    async def before_run(
        self,
        ctx: RunContext,
    ) -> None:
        """
        Persist the current user message.
        """

        conversation = ctx.session.conversation_context

        if (
            conversation is None
            or not ctx.messages
        ):
            return

        await self._provider.append(
            conversation=conversation,
            message=ctx.messages[0],
        )

    async def after_llm(
        self,
        ctx: RunContext,
        event: AfterLLMEvent,
    ) -> None:
        """
        Persist the assistant message.
        """

        conversation = ctx.session.conversation_context

        if conversation is None:
            return

        await self._provider.append(
            conversation=conversation,
            message=event.message,
        )

    async def after_tools(
        self,
        ctx: RunContext,
        event: AfterToolsEvent,
    ) -> None:
        """
        Persist tool messages.
        """

        if not event.messages:
            return

        conversation = ctx.session.conversation_context

        if conversation is None:
            return

        await self._provider.append_many(
            conversation=conversation,
            messages=event.messages,
        )
