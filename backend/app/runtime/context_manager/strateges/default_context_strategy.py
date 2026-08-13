from __future__ import annotations

import logging

from app.runtime.chat.message import ChatMessage
from app.runtime.context_manager.optimizers.default_optimizer import (
    DefaultConversationOptimizer,
)
from app.runtime.context_manager.optimizers.optimizer import (
    ContextOptimizer,
)
from app.runtime.prompts.builder import PromptBuilder

from ..context import ContextBudget
from .strategy import ContextStrategy

logger = logging.getLogger(__name__)


class DefaultContextStrategy(
    ContextStrategy,
):
    """
    Default conversation optimization strategy.

    Responsibilities
    ----------------
    - Build the prompt when requested.
    - Coordinate conversation optimization.
    - Pass the already-measured context size to the optimizer.

    The ContextMonitor determines WHEN optimization is
    required.

    The ContextOptimizer performs the actual optimization.

    PromptState contains only stable prompt components.
    Conversation history remains dynamic and is rebuilt
    from ConversationContext.

    This strategy does not:

    - build a prompt to calculate its size
    - count tokens
    - repeatedly rebuild prompts
    - perform emergency trimming
    """

    #
    # When the context reaches the monitor threshold,
    # compress it to approximately 80% of that threshold.
    #
    # Example:
    #
    # threshold = 10,500
    # target    = 8,400
    #
    # This creates headroom for the next messages.
    #
    OPTIMIZATION_TARGET_RATIO = 0.80

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
        """
        Build the prompt for the actual LLM inference.

        No token counting or conversation optimization
        is performed here.
        """

        return await builder.build()

    async def optimize(
        self,
        builder: PromptBuilder,
    ) -> bool:
        """
        Optimize the conversation after the ContextMonitor
        has determined that the configured threshold was reached.

        The approximate context token count was already
        calculated by RunContext.

        No additional token counting is performed here.
        """

        conversation_provider = (
            builder.context.agent.conversation
        )

        if conversation_provider is None:

            logger.debug(
                "Conversation optimization skipped: "
                "no conversation provider is configured.",
            )

            return False

        llm = builder.context.agent.llm

        budget = ContextBudget.from_llm(
            llm,
        )

        if budget.max_prompt_tokens is None:

            logger.debug(
                "Conversation optimization skipped: "
                "LLM does not expose a maximum prompt size.",
            )

            return False

        run_context = (
            builder.context.run_context
        )

        #
        # This value was already calculated by the
        # ContextMonitor when the runtime message was added.
        #
        current_tokens = (
            run_context.context_tokens
        )

        if current_tokens <= 0:

            logger.debug(
                "Conversation optimization skipped: "
                "no context token measurement is available.",
            )

            return False

        #
        # The monitor owns the optimization trigger.
        #
        threshold = (
            run_context.session.context_monitor.threshold
        )

        logger.debug(
            "Context threshold reached at approximately "
            "%s tokens. Threshold: %s.",
            current_tokens,
            threshold,
        )

        #
        # Create headroom below the trigger threshold.
        #
        target_tokens = int(
            threshold
            * self.OPTIMIZATION_TARGET_RATIO
        )

        #
        # Never request a target larger than the model's
        # available prompt budget.
        #
        target_tokens = min(
            target_tokens,
            budget.max_prompt_tokens,
        )

        #
        # Make sure the target is actually below the
        # current context size.
        #
        if target_tokens >= current_tokens:

            logger.debug(
                "Conversation optimization skipped: "
                "target tokens (%s) are not below "
                "current tokens (%s).",
                target_tokens,
                current_tokens,
            )

            return False

        logger.debug(
            "Optimizing conversation from approximately "
            "%s tokens to approximately %s tokens.",
            current_tokens,
            target_tokens,
        )

        #
        # Use the configured optimizer when supplied.
        #
        optimizer = self._optimizer

        #
        # Otherwise create the default optimizer for
        # the current conversation provider.
        #
        if optimizer is None:

            optimizer = DefaultConversationOptimizer(
                provider=conversation_provider,
            )

        #
        # IMPORTANT:
        #
        # current_tokens came from ContextMonitor.
        #
        # No second token count happens here.
        #
        result = await optimizer.optimize(
            conversation=(
                builder.context.conversation_context
            ),
            current_tokens=current_tokens,
            target_tokens=target_tokens,
        )

        if result.optimized:

            logger.info(
                "Conversation optimized successfully. "
                "Target: approximately %s tokens.",
                target_tokens,
            )

            return True

        if result.exhausted:

            logger.warning(
                "Conversation optimization exhausted. "
                "Reason: %s",
                result.reason,
            )

            return False

        logger.debug(
            "Conversation optimization made no changes. "
            "Reason: %s",
            result.reason,
        )

        return False
