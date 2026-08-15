from __future__ import annotations

import asyncio
import logging

from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from app.runtime.events.events import (
    EventType,
    Status,
    StatusEvent,
)

from app.runtime.chat.message import ChatMessage
from app.runtime.context_manager.optimizers.default_optimizer import (
    DefaultConversationOptimizer,
)
from app.runtime.context_manager.optimizers.optimizer import (
    ContextOptimizer,
)
from app.runtime.prompts.builder import PromptBuilder

from .strategy import ContextStrategy

logger = logging.getLogger(__name__)


class DefaultContextStrategy(
    ContextStrategy,
):
    """
    Default conversation optimization strategy.

    The current user message is immutable and is never
    summarized or deleted.

    Optimization only affects persisted conversation
    messages and retains a minimum amount of previous
    conversation.

    A single optimization phase can contain multiple
    optimizer passes. Once the phase finishes, the
    threshold trigger is reset so a future message can
    trigger a new optimization phase.
    """

    OPTIMIZATION_FLOOR_RATIO = 0.10

    MIN_CONVERSATION_RETENTION_RATIO = 0.10

    def __init__(
        self,
        *,
        optimizer: ContextOptimizer | None = None,
    ) -> None:

        self._optimizer = optimizer

    async def build(
        self,
        builder: PromptBuilder,
    ) -> list[ChatMessage]:

        return await builder.build()

    async def optimize(
        self,
        builder: PromptBuilder,
    ) -> bool:

        conversation_provider = (
            builder.context.agent.conversation
        )

        if conversation_provider is None:

            return False

        run_context = (
            builder.context.run_context
        )

        current_tokens = (
            run_context.context_tokens
        )

        if current_tokens <= 0:

            return False

        initial_tokens = current_tokens

        threshold = (
            run_context.session.context_monitor.threshold
        )

        full_context_floor = max(
            1,
            int(
                threshold
                * self.OPTIMIZATION_FLOOR_RATIO
            ),
        )

        conversation_retention_floor = max(
            1,
            int(
                threshold
                * self.MIN_CONVERSATION_RETENTION_RATIO
            ),
        )

        current_user_message = (
            run_context.current_user_message
        )

        if current_user_message is None:

            run_context.mark_context_optimized(
                current_tokens,
            )

            return False

        current_user_tokens = (
            count_tokens_approximately(
                builder.context.agent.llm.to_provider_messages(
                    [current_user_message],
                ),
            )
        )

        minimum_safe_context = (
            current_user_tokens
            + conversation_retention_floor
        )

        optimization_target = max(
            full_context_floor,
            minimum_safe_context,
        )

        if optimization_target >= current_tokens:

            run_context.mark_context_optimized(
                current_tokens,
            )

            return False

        optimizer = self._optimizer

        if optimizer is None:

            optimizer = DefaultConversationOptimizer(
                provider=conversation_provider,
            )

        optimized = False

        while current_tokens > optimization_target:
            await run_context.emitter.emit(
                EventType.PROGRESS,
                StatusEvent(
                    status=Status.SUMMARIZING,
                ),
            )
            await asyncio.sleep(0)

            tokens_before = current_tokens

            logger.debug(
                "Optimization pass started. "
                "Current: %s. "
                "Target: %s.",
                tokens_before,
                optimization_target,
            )

            result = await optimizer.optimize(
                conversation=(
                    builder.context.conversation_context
                ),
                current_tokens=tokens_before,
                target_tokens=optimization_target,
                run_context=run_context,
            )

            if not result.optimized:

                if result.exhausted:

                    logger.warning(
                        "Conversation optimization exhausted. "
                        "Current: %s. "
                        "Target: %s. "
                        "Reason: %s",
                        tokens_before,
                        optimization_target,
                        result.reason,
                    )
                break

            optimized = True

            #
            # Conversation changed, so the previously prepared
            # stable prompt is stale.
            #
            prompt_state = (
                builder.context.prompt_state
            )

            prompt_state.stable_messages.clear()
            prompt_state.prepared = False

            #
            # Rebuild the stable prompt so the next measurement
            # includes the updated conversation, memory, RAG,
            # instructions, output formatting, and templates.
            #
            await builder.prepare()

            #
            # Measure the same full runtime context that will
            # be used for inference.
            #
            current_tokens = (
                run_context.session.context_monitor.count(
                    conversation_context=(
                        builder.context.conversation_context
                    ),
                    run_context=run_context,
                    stable_messages=(
                        prompt_state.stable_messages
                    ),
                )
            )

            run_context.update_context_tokens(
                current_tokens,
            )

            tokens_saved = max(
                0,
                tokens_before - current_tokens,
            )

            logger.info(
                "Conversation optimization pass completed. "
                "Full context before: %s. "
                "Full context after: %s. "
                "Context reduction: %s.",
                tokens_before,
                current_tokens,
                tokens_saved,
            )

            if current_tokens >= tokens_before:
                break

        total_tokens_saved = max(
            0,
            initial_tokens - current_tokens,
        )

        if optimized:

            logger.info(
                "Conversation optimization phase completed. "
                "Initial full context: %s. "
                "Final full context: %s. "
                "Total context reduction: %s. "
                "Target: %s.",
                initial_tokens,
                current_tokens,
                total_tokens_saved,
                optimization_target,
            )

        run_context.mark_context_optimized(
            current_tokens,
        )

        await run_context.emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.SUMMARY_COMPLETE,
            ),
        )
        return optimized
