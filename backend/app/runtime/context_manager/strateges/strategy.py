from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.chat.message import ChatMessage
    from app.runtime.prompts.builder import PromptBuilder


class ContextStrategy(ABC):
    """
    Strategy used by ContextManager to build prompts
    and optimize conversation context.

    The strategy does not determine when optimization
    is required.

    That decision is made by the runtime ContextMonitor.
    """

    @abstractmethod
    async def build(
        self,
        builder: PromptBuilder,
    ) -> list[ChatMessage]:
        """
        Build the prompt for LLM inference.

        Prompt construction happens only when the LLM
        is ready to execute.
        """
        ...

    @abstractmethod
    async def optimize(
        self,
        builder: PromptBuilder,
    ) -> bool:
        """
        Optimize the conversation after the runtime has
        determined that the context threshold was reached.

        The strategy must not perform another token count
        to determine whether optimization is required.

        Returns
        -------
        bool
            True when the conversation was successfully
            optimized, otherwise False.
        """
        ...
