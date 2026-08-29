from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from app.runtime.chat.message import ChatMessage

from .monitor import ContextMonitor

if TYPE_CHECKING:
    from app.runtime.agents.run_context import RunContext
    from app.runtime.conversation.context import ConversationContext


class DefaultContextMonitor(
    ContextMonitor,
):
    """
    Default context monitor.

    Uses LangChain's approximate token counter to measure
    the runtime context.

    The monitor does not:

    - build prompts
    - optimize conversations
    - modify conversation state
    - persist token counts
    - cache token counts
    - decide when optimization should run

    It only performs the requested measurement and checks
    an already-calculated measurement against the threshold.
    """

    def __init__(
        self,
        *,
        threshold: int,
    ) -> None:

        if threshold <= 0:
            raise ValueError(
                "Context threshold must be greater than zero.",
            )

        self._threshold = threshold

    @property
    def threshold(
        self,
    ) -> int:
        """
        Token threshold at which conversation optimization
        should be triggered.
        """

        return self._threshold

    def count(
        self,
        *,
        conversation_context: ConversationContext,
        run_context: RunContext,
        stable_messages: list[ChatMessage] | None = None,
    ) -> int:
        """
        Estimate the current runtime context size.

        When stable_messages are provided, they already contain the
        prepared stable prompt, including conversation, memory, RAG,
        instructions, output formatting, and template messages.

        Current execution messages are always added separately.
        """

        messages: list[ChatMessage] = []

        if stable_messages:
            messages.extend(
                message
                for message in stable_messages
                if message.content
            )

        else:
            if conversation_context.summary:

                messages.append(
                    ChatMessage.system(
                        conversation_context.summary.strip(),
                    ),
                )

            messages.extend(
                message
                for message in conversation_context.messages
                if message.content
            )

        messages.extend(
            message
            for message in run_context.messages
            if message.content
        )

        if not messages:
            return 0

        return count_tokens_approximately(
            run_context.agent.llm.to_provider_messages(
                messages=messages,
            )
        )

    def reached(
        self,
        token_count: int,
    ) -> bool:
        """
        Check whether an already-calculated token count
        has reached or exceeded the configured threshold.

        No token counting is performed here.
        """

        return token_count >= self._threshold
