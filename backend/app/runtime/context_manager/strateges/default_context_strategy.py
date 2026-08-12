from __future__ import annotations

import logging

from langchain_core.messages import trim_messages
from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from app.runtime.chat.message import ChatMessage
from app.runtime.prompts.builder import PromptBuilder

from ..context import ContextBudget
from .strategy import ContextStrategy

logger = logging.getLogger(__name__)


class DefaultContextStrategy(
    ContextStrategy,
):
    """
    Default context optimization strategy.

    Strategy
    --------
    1. Build the prompt.
    2. Count prompt tokens.
    3. If it fits, return it.
    4. Otherwise optimize the conversation.
    5. If optimization succeeds, rebuild the prompt.
    6. Repeat until either:
       - the prompt fits, or
       - conversation optimization is exhausted.
    7. Perform one emergency trim as a last resort.
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

        provider_messages = []
        current_tokens = 0

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

            current_tokens = (
                await llm.token_counter.count(
                    provider_messages,
                )
            )

            logger.debug(
                "Prompt tokens: %s / %s",
                current_tokens,
                budget.max_prompt_tokens,
            )

            #
            # Prompt fits.
            #
            if (
                current_tokens
                <= budget.max_prompt_tokens
            ):
                return messages

            if conversation is None:
                break

            result = await conversation.optimize(
                conversation=builder.context.conversation_context,
                current_tokens=current_tokens,
                target_tokens=budget.max_prompt_tokens,
            )

            if result.optimized:
                continue

            if result.exhausted:
                break

        trimmed = trim_messages(
            provider_messages,
            max_tokens=budget.max_prompt_tokens,
            strategy="last",
            token_counter=count_tokens_approximately,
            start_on="human",
            include_system=False,
        )

        trimmed_tokens = (
            await llm.token_counter.count(
                trimmed,
            )
        )

        logger.warning(
            "Emergency trimming reduced "
            "prompt from %s to %s tokens.",
            current_tokens,
            trimmed_tokens,
        )

        return ChatMessage.from_provider_messages(
            trimmed,
        )
