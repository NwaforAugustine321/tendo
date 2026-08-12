from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import trim_messages
from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from ..context import ContextBudget
from ..exception import ContextOptimizationFailed
from .strategy import ContextStrategy

if TYPE_CHECKING:
    from app.runtime.chat.message import ChatMessage
    from app.runtime.prompts.builder import PromptBuilder

logger = logging.getLogger(__name__)


class DefaultContextStrategy(
    ContextStrategy,
):
    """
    Default context optimization strategy.

    Strategy
    --------
    1. Build the prompt.
    2. Check the prompt budget.
    3. If it fits, return it.
    4. Otherwise attempt conversation optimization.
    5. Rebuild and repeat until the conversation
       optimizer is exhausted.
    6. As a final fallback, trim the prompt.
    """

    async def build(
        self,
        builder: PromptBuilder,
    ) -> list[ChatMessage]:

        llm = builder.context.agent.llm

        budget = ContextBudget.from_llm(
            llm,
        )

        if budget.max_prompt_tokens is None:
            return await builder.build()

        conversation = (
            builder.context.agent.conversation
        )

        while True:

            #
            # Build the latest prompt.
            #
            messages = await builder.build()

            provider_messages = (
                llm.to_provider_messages(
                    messages,
                )
            )

            tokens = await llm.token_counter.count(
                provider_messages,
            )

            #
            # Prompt already fits.
            #
            if tokens <= budget.max_prompt_tokens:
                return messages

            #
            # No conversation provider.
            #
            if conversation is None:
                break

            #
            # Give the conversation provider one
            # opportunity to reduce the prompt.
            #
            result = await conversation.optimize(
                conversation=builder.context.conversation_context,
                target_tokens=budget.max_prompt_tokens,
            )

            #
            # Conversation changed.
            #
            if result.optimized:
                logger.info(
                    "Conversation optimized "
                    "(saved ≈ %s tokens).",
                    result.estimated_tokens_saved,
                )
                continue

            #
            # Provider has more strategies.
            #
            if not result.exhausted:
                continue

            #
            # Conversation optimization is exhausted.
            #
            logger.info(
                "Conversation optimization exhausted. "
                "Falling back to emergency trimming."
            )

            break

        #
        # Last resort:
        # trim the prompt.
        #
        trimmed = trim_messages(
            provider_messages,
            max_tokens=budget.max_prompt_tokens,
            strategy="last",
            token_counter=count_tokens_approximately,
            start_on="human",
            include_system=True,
        )

        trimmed_tokens = await llm.token_counter.count(
            trimmed,
        )

        if trimmed_tokens <= budget.max_prompt_tokens:

            logger.warning(
                "Prompt exceeded the model context "
                "window. Emergency trimming was "
                "applied."
            )

            return ChatMessage.from_provider_messages(
                trimmed,
            )

        raise ContextOptimizationFailed(
            "Unable to reduce the prompt to fit "
            "within the model context window."
        )
