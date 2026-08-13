from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.agents.run_context import RunContext
    from app.runtime.conversation.context import ConversationContext


class ContextMonitor(ABC):
    """
    Monitors the approximate size of the runtime context.
    """

    @property
    @abstractmethod
    def threshold(
        self,
    ) -> int:
        """
        Approximate token threshold at which context
        optimization should be triggered.
        """
        ...

    @abstractmethod
    def count(
        self,
        *,
        conversation_context: ConversationContext,
        run_context: RunContext,
    ) -> int:
        """
        Calculate the current approximate context size.

        The calculation should be performed from the
        current conversation and runtime state rather
        than from cached token counts.
        """
        ...

    @abstractmethod
    def reached(
        self,
        *,
        conversation_context: ConversationContext,
        run_context: RunContext,
    ) -> bool:
        """
        Return True when the approximate context size
        reaches or exceeds the configured threshold.
        """
        ...
