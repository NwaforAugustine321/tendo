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
    Default conversation optimizer.

    The optimizer receives the approximate context size
    that was already calculated by ContextMonitor.

    It does not perform token counting.

    Optimization pipeline
    ---------------------
    1. Receive the existing context token count.
    2. Determine how much context must be compressed.
    3. Select the oldest messages while preserving
       recent messages.
    4. Merge selected messages with the existing summary.
    5. Generate a new rolling summary.
    6. Persist the summary.
    7. Delete the summarized messages.
    8. Reload the conversation.

    The next context measurement is performed by
    ContextMonitor when another runtime message is added.
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
        """
        Perform one conversation optimization pass.

        Parameters
        ----------
        conversation:
            Conversation being optimized.

        current_tokens:
            Approximate context size already calculated
            by ContextMonitor.

        target_tokens:
            Desired context size after optimization.

        No token counting is performed here.
        """

        try:

            if conversation.empty:

                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason=(
                        "Conversation is empty."
                    ),
                )

            tokens_to_recover = (
                current_tokens
                - target_tokens
            )

            if tokens_to_recover <= 0:

                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason=(
                        "No optimization required."
                    ),
                )

            messages = (
                self._messages_to_summarize(
                    conversation=conversation,
                    tokens_to_recover=tokens_to_recover,
                )
            )
            print('message ', len(messages))
            if not messages:

                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason=(
                        "Conversation cannot be "
                        "compressed further."
                    ),
                )

            #
            # Include the previous summary so the new
            # summary represents the accumulated history.
            #
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

            logger.info(
                "Summarizing conversation at approximately "
                "%s tokens.",
                current_tokens,
            )

            summary = (
                await self._summarizer.summarize(
                    messages=summary_messages,
                    target_tokens=min(
                        target_tokens,
                        self.SUMMARY_TARGET_TOKENS,
                    ),
                    instructions=(
                        self.SUMMARY_INSTRUCTIONS
                    ),
                )
            )

            #
            # Persist the new rolling summary.
            #
            await self._provider.update_summary(
                conversation=conversation,
                summary=summary,
            )

            #
            # Remove the messages represented by the
            # new summary.
            #
            await self._provider.delete_messages(
                conversation=conversation,
                messages=messages,
            )

            #
            # Reload the same ConversationContext so the
            # in-memory context reflects the persisted state.
            #
            await self._provider.reload(
                conversation=conversation,
            )

            logger.info(
                "Conversation optimization completed. "
                "Summarized %s messages.",
                len(messages),
            )

            #
            # Do not claim an exact token saving.
            #
            # The actual post-optimization context size will
            # be measured by ContextMonitor on the next
            # runtime message.
            #
            return OptimizationResult(
                optimized=True,
                exhausted=False,
                estimated_tokens_saved=0,
                reason=(
                    "Conversation summarized."
                ),
            )

        except Exception as error:

            logger.exception(
                "Conversation optimization failed.",
            )

            return OptimizationResult(
                optimized=False,
                exhausted=True,
                reason=(
                    "Conversation optimization failed: "
                    f"{error}"
                ),
            )

    def _messages_to_summarize(
        self,
        *,
        conversation: ConversationContext,
        tokens_to_recover: int,
    ) -> list[ChatMessage]:
        """
        Select enough oldest messages to recover the
        requested approximate budget while keeping the
        most recent messages verbatim.

        The lightweight character approximation here is
        ONLY used to select which messages should be
        summarized.

        It does NOT determine whether optimization should
        happen.
        """

        messages = (
            self._conversation_messages(
                conversation,
            )
        )

        if (
            len(messages)
            <= self.KEEP_RECENT_MESSAGES
        ):
            return []

        candidates = messages[
            :-self.KEEP_RECENT_MESSAGES
        ]

        recovered = 0

        selected: list[ChatMessage] = []

        for message in candidates:

            selected.append(
                message,
            )

            content = (
                message.content
                if isinstance(
                    message.content,
                    str,
                )
                else str(
                    message.content,
                )
            )

            #
            # Lightweight selection estimate.
            #
            recovered += (
                len(content) // 4
            )

            if recovered >= tokens_to_recover:
                break

        return selected

    def _conversation_messages(
        self,
        conversation: ConversationContext,
    ) -> list[ChatMessage]:
        """
        Return persisted conversation messages.

        Runtime system messages are excluded because they
        are not part of the conversational history that
        should be summarized.
        """

        return [
            message
            for message in conversation.messages
            if message.role != "system"
        ]
