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
from app.runtime.chat.message import ChatMessage


class ConversationMiddleware(
    AgentMiddleware,
):
    """
    Synchronizes the in-memory conversation with the
    persistent conversation store.

    Uses ChatMessage.to_dicts() to strip messages down
    to role+content before persistence.
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
        ):
            return

        user_request = ctx.session.run_context.user_request

        if not user_request:
            return

        msg = ChatMessage.user(user_request)

        await self._provider.append(
            conversation=conversation,
            message=msg,
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

        if len(ctx.messages) == 0:
            return

        msg = next(
            (
                message
                for message in reversed(ctx.messages)
                if message.role == "assistant"
            ),
            None,
        )

        await self._provider.append(
            conversation=conversation,
            message=msg,
        )

    # async def after_tools(
    #     self,
    #     ctx: RunContext,
    #     event: AfterToolsEvent,
    # ) -> None:
    #     """
    #     Persist non-tool messages from the tool execution.
    #     """

    #     if not event.messages:
    #         return

    #     conversation = ctx.session.conversation_context

    #     if conversation is None:
    #         return

    #     # to_dicts already filters out tool messages
    #     storable = ChatMessage.to_dicts(event.messages)

    #     if not storable:
    #         return

    #     storable_messages = ChatMessage.from_dicts(storable)

    #     if storable_messages:
    #         await self._provider.append_many(
    #             conversation=conversation,
    #             messages=storable_messages,
    #         )
