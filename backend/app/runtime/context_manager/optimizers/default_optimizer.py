from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from app.runtime.agents.run_context import RunContext
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


SELECTION_BUFFER_RATIO = 0.08


class DefaultConversationOptimizer(
    ContextOptimizer,
):
    """
    Default conversation optimizer.

    The optimizer receives the approximate full runtime
    context size already calculated by ContextMonitor.

    It does NOT optimize the current user message.

    Only persisted conversation messages are eligible
    for summarization and deletion.

    Responsibilities
    ----------------
    - Determine how many persisted conversation tokens
      need to be recovered.
    - Select the oldest eligible messages.
    - Apply a 30% message-count selection buffer.
    - Merge selected messages with the existing summary.
    - Generate a rolling summary.
    - Persist the summary.
    - Delete summarized messages.
    - Reload the conversation.

    """

    #
    # Always keep the most recent persisted messages
    # verbatim.
    #
    KEEP_RECENT_MESSAGES = 20

    #
    # Maximum size of the generated rolling summary.
    #
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
        run_context: RunContext,
    ) -> OptimizationResult:
        """
        Perform one conversation optimization pass.

        Parameters
        ----------
        conversation:
            Persisted conversation being optimized.

        current_tokens:
            Approximate FULL runtime context size already
            calculated by ContextMonitor.

            This includes the current user message.

        target_tokens:
            Safe target calculated by ContextStrategy.

        run_context:
            Current agent execution context.


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
                    run_context=run_context,
                )
            )

            if not messages:

                return OptimizationResult(
                    optimized=False,
                    exhausted=True,
                    reason=(
                        "Conversation cannot be "
                        "compressed further."
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

            logger.info(
                "Summarizing conversation at approximately "
                "%s tokens. "
                "Target: %s tokens. "
                "Tokens to recover: %s. "
                "Selected messages: %s.",
                current_tokens,
                target_tokens,
                tokens_to_recover,
                len(messages),
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

            estimated_tokens_saved = (
                self._count_message_tokens(
                    messages=messages,
                    run_context=run_context,
                )
            )

            logger.info(
                "Conversation optimization completed. "
                "Summarized %s messages. "
                "Estimated removed message tokens: %s.",
                len(messages),
                estimated_tokens_saved,
            )

            return OptimizationResult(
                optimized=True,
                exhausted=False,
                estimated_tokens_saved=(
                    estimated_tokens_saved
                ),
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
        run_context: RunContext,
    ) -> list[ChatMessage]:
        """
        Select persisted conversation messages for
        summarization.

        The current user message is NOT part of this
        collection.

        Selection rules
        ---------------

        1. Always preserve KEEP_RECENT_MESSAGES.

        2. Calculate the real approximate token count
           of all eligible candidates.

        3. If all candidates fit within tokens_to_recover,
           summarize all candidates.

        4. Otherwise select the oldest messages until
           tokens_to_recover is reached.

        5. Add a 30% message-count buffer.

        Example
        -------
        Required messages = 30
        Buffer = 30%

        30 + ceil(30 * 0.30)
        = 40 messages

        If there are 50 eligible messages:

            40 messages -> summarized
            10 messages -> retained
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
            :-self.KEEP_RECENT_MESSAGES
        ]

        if not candidates:
            return []

        candidate_tokens = (
            self._count_message_tokens(
                messages=candidates,
                run_context=run_context,
            )
        )

        if candidate_tokens <= tokens_to_recover:

            logger.debug(
                "All candidate messages fit within the "
                "recovery budget. "
                "Candidate tokens: %s. "
                "Tokens to recover: %s. "
                "Messages selected: %s.",
                candidate_tokens,
                tokens_to_recover,
                len(candidates),
            )

            return candidates

        recovered_tokens = 0

        required_message_count = 0

        for message in candidates:

            message_tokens = (
                self._count_message_tokens(
                    messages=[message],
                    run_context=run_context,
                )
            )

            recovered_tokens += message_tokens

            required_message_count += 1

            if recovered_tokens >= tokens_to_recover:
                break

        buffered_message_count = (
            required_message_count
            + math.ceil(
                required_message_count
                * SELECTION_BUFFER_RATIO,
            )
        )

        buffered_message_count = min(
            buffered_message_count,
            len(candidates),
        )

        selected = candidates[
            :buffered_message_count
        ]

        selected_tokens = (
            self._count_message_tokens(
                messages=selected,
                run_context=run_context,
            )
        )

        logger.debug(
            "Conversation message selection completed. "
            "Tokens to recover: %s. "
            "Candidate tokens: %s. "
            "Recovered before buffer: %s. "
            "Required messages: %s. "
            "Buffered messages: %s. "
            "Selected messages: %s. "
            "Selected tokens: %s.",
            tokens_to_recover,
            candidate_tokens,
            recovered_tokens,
            required_message_count,
            buffered_message_count,
            len(selected),
            selected_tokens,
        )

        return selected

    def _count_message_tokens(
        self,
        *,
        messages: list[ChatMessage],
        run_context: RunContext,
    ) -> int:
        """
        Count approximate tokens for persisted messages.
        """

        if not messages:
            return 0

        provider_messages = (
            run_context.agent.llm.to_provider_messages(
                messages,
            )
        )

        return count_tokens_approximately(
            provider_messages,
        )

    def _conversation_messages(
        self,
        conversation: ConversationContext,
    ) -> list[ChatMessage]:
        """
        Return persisted conversation messages eligible
        for optimization.

        Runtime system messages are excluded.
        """

        return [
            message
            for message in conversation.messages
            if message.role != "system"
        ]
