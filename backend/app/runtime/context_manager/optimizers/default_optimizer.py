from __future__ import annotations

from typing import TYPE_CHECKING

from app.runtime.chat.message import ChatMessage

from .optimizer import (
    ContextOptimizer,
    OptimizationResult,
)
from app.runtime.summarizers.summarizer import Summarizer
from app.runtime.summarizers.default_summarizer import DefaultSummarizer
import logging


if TYPE_CHECKING:
    from app.runtime.conversation.context import ConversationContext
    from app.runtime.conversation.provider import ConversationProvider

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
        Replace the previous summary with a new one that
        contains both the previous summary and the new
        conversation.
"""


class DefaultConversationOptimizer(
    ContextOptimizer,
):
    """
    Default conversation optimization strategy.

    Optimization pipeline
    ---------------------
    1. Select a batch of old messages.
    2. Merge them with the previous summary.
    3. Generate a new rolling summary.
    4. Persist the summary.
    5. Delete summarized messages.
    6. Reload the conversation.
    """

    SUMMARY_BATCH_SIZE = 25

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
        target_tokens: int,
    ) -> OptimizationResult:

        try:

            if conversation.empty:
                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason="Conversation is empty.",
                )

            if not self._should_summarize(
                conversation,
            ):
                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason=(
                        "Conversation cannot be "
                        "compressed further."
                    ),
                )

            messages = self._messages_to_summarize(
                conversation,
            )

            if not messages:
                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason=(
                        "No messages selected for "
                        "summarization."
                    ),
                )

            #
            # Build rolling summary.
            #
            summary_messages: list[ChatMessage] = []

            if conversation.summary:
                summary_messages.append(
                    ChatMessage.user(
                        (
                            "Previous conversation "
                            "summary:\n\n"
                            f"{conversation.summary}"
                        )
                    )
                )

            summary_messages.extend(
                messages,
            )

            summary = await self._summarizer.summarize(
                messages=summary_messages,
                target_tokens=min(
                    target_tokens,
                    self.SUMMARY_TARGET_TOKENS,
                ),
                instructions=self.SUMMARY_INSTRUCTIONS,
            )

            logger.info(f"Summarizing conversation: {summary}")

            conversation.summary = summary

            # Remove summarized messages from the conversation
            conversation.messages = conversation.messages[len(messages):]

            await self._provider.update_summary(
                conversation=conversation,
                summary=summary,
            )

            return OptimizationResult(
                optimized=True,
                exhausted=False,
                estimated_tokens_saved=max(
                    0,
                    len(messages) * 100
                    - self.SUMMARY_TARGET_TOKENS,
                ),
                reason="Conversation summarized.",
            )

        except Exception as e:
            logger.warning(f"Optimization failed: {e}")
            return OptimizationResult(
                optimized=False,
                exhausted=True,
                reason=f"Optimization error: {e}",
            )

    def _should_summarize(
        self,
        conversation: ConversationContext,
    ) -> bool:
        """
        Determine whether there are messages
        available to summarize. Summarize whenever
        there are more messages than we want to keep.
        """

        non_system = [
            m for m in conversation.messages
            if m.role != "system"
        ]

        # Need at least 1 message beyond what we keep
        return len(non_system) > self.KEEP_RECENT_MESSAGES

    def _messages_to_summarize(
        self,
        conversation: ConversationContext,
    ) -> list[ChatMessage]:
        """
        Select messages to summarize — everything
        except the most recent KEEP_RECENT_MESSAGES.
        """

        available = (
            len(conversation.messages)
            - self.KEEP_RECENT_MESSAGES
        )

        if available <= 0:
            return []

        return conversation.messages[:available]
