from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.chat.message import ChatMessage


class ContextMonitor(ABC):
    """
    Monitors the approximate size of the runtime context.

    The monitor does not build prompts, optimize conversations,
    or modify conversation state. It only determines whether
    the context has reached the configured threshold.
    """

    @abstractmethod
    def count(
        self,
        messages: list[ChatMessage],
    ) -> int:
        """
        Estimate the number of tokens in the given messages.
        """
        ...

    @abstractmethod
    def reached(
        self,
        messages: list[ChatMessage],
    ) -> bool:
        """
        Return True when the approximate token count reaches
        the configured threshold.
        """
        ...
