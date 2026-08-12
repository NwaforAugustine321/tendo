from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.runtime.chat.message import ChatMessage
from app.runtime.summarizers.default_summarizer import (
    DefaultSummarizer,
)
from app.runtime.summarizers.summarizer import (
    Summarizer,
)

from .optimizer import (
    ContextOptimizer,
    OptimizationResult,
)

if TYPE_CHECKING:
    from app.runtime.conversation.context import (
        ConversationContext,
    )
    from app.runtime.conversation.provider import (
        ConversationProvider,
    )

logger = logging.getLogger(__name__)

PROMPT = """
Summarize the conversation while preserving:

- User goals
- Decisions
- Constraints
- Preferences
- Important facts
- Outstanding tasks
- Open questions
- Context

Do not invent information.

If a previous summary exists, merge it into the
new summary so the result fully represents the
conversation so far.

Return only the summary.
"""


class DefaultConversationOptimizer(
    ContextOptimizer,
):
    """
    Default conversation optimization strategy.

    Optimization pipeline
    ---------------------
    1. Determine how many tokens must be recovered.
    2. Select enough oldest messages.
    3. Merge them with the previous summary.
    4. Generate a new rolling summary.
    5. Persist the summary.
    6. Delete summarized messages.
    7. Reload the conversation.
    """

    KEEP_RECENT_MESSAGES = 20

    SUMMARY_TARGET_TOKENS = 400

    SUMMARY_INSTRUCTIONS = PROMPT

    def __init__(
        self,
        *,
        provider: ConversationProvider,
        summarizer: Summarizer | None = None,
    ) -> None:

        self._provider = provider

        self._summarizer = (
            summarizer
            if summarizer is not None
            else DefaultSummarizer()
        )

    async def optimize(
        self,
        *,
        conversation: ConversationContext,
        current_tokens: int,
        target_tokens: int,
    ) -> OptimizationResult:

        try:

            if conversation.empty:

                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason="Conversation is empty.",
                )

            tokens_to_recover = (
                current_tokens
                - target_tokens
            )

            if tokens_to_recover <= 0:

                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason="No optimization required.",
                )

            messages = self._messages_to_summarize(
                conversation=conversation,
                tokens_to_recover=tokens_to_recover,
            )

            if not messages:

                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason=(
                        "Conversation cannot "
                        "be compressed further."
                    ),
                )

            summary_messages: list[
                ChatMessage
            ] = []

            if conversation.summary:

                summary_messages.append(
                    ChatMessage.summary(
                        conversation.summary,
                    )
                )

            summary_messages.extend(
                messages,
            )

            logger.info('Summarizing the session conversation')
            summary = await self._summarizer.summarize(
                messages=summary_messages,
                target_tokens=min(
                    target_tokens,
                    self.SUMMARY_TARGET_TOKENS,
                ),
                instructions=self.SUMMARY_INSTRUCTIONS,
            )

            await self._provider.update_summary(
                conversation=conversation,
                summary=summary,
            )

            await self._provider.delete_messages(
                conversation=conversation,
                messages=messages,
            )

            await self._provider.reload(
                conversation=conversation,
            )

            return OptimizationResult(
                optimized=True,
                exhausted=False,
                estimated_tokens_saved=(
                    current_tokens - target_tokens
                ),
                reason="Conversation summarized.",
            )

        except Exception as e:

            return OptimizationResult(
                optimized=False,
                exhausted=True,
                reason=(
                    "Conversation optimization "
                    "failed."
                ),
            )

    def _messages_to_summarize(
        self,
        *,
        conversation: ConversationContext,
        tokens_to_recover: int,
    ) -> list[ChatMessage]:
        """
        Select enough oldest messages to recover
        the requested token budget while keeping
        the most recent messages verbatim.
        """

        messages = self._conversation_messages(
            conversation,
        )

        if (
            len(messages)
            <= self.KEEP_RECENT_MESSAGES
        ):
            return []

        candidates = messages[
            : -self.KEEP_RECENT_MESSAGES
        ]

        recovered = 0

        selected: list[
            ChatMessage
        ] = []

        for message in candidates:

            selected.append(
                message,
            )

            content = (
                message.content
                if isinstance(message.content, str)
                else str(message.content)
            )

            recovered += len(content) // 4

            if recovered >= tokens_to_recover:
                break

        return selected

    def _conversation_messages(
        self,
        conversation: ConversationContext,
    ) -> list[ChatMessage]:
        """
        Return persisted conversation messages.

        Runtime system messages are excluded.
        """

        return [
            message
            for message in conversation.messages
            if message.role != "system"
        ]
