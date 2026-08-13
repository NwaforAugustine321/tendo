from __future__ import annotations

from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from app.runtime.chat.message import ChatMessage

from .monitor import ContextMonitor


class DefaultContextMonitor(
    ContextMonitor,
):
    """
    Default context monitor.

    """

    def __init__(
        self,
        *,
        threshold: int,
    ) -> None:

        if threshold <= 0:
            raise ValueError(
                "Context threshold must be greater than zero.",
            )

        self._threshold = threshold

    @property
    def threshold(
        self,
    ) -> int:
        """
        Token threshold at which conversation optimization
        should be triggered.
        """

        return self._threshold

    def count(
        self,
        messages: list[ChatMessage],
    ) -> int:
        """
        Estimate the number of tokens in the messages.
        """

        return count_tokens_approximately(
            messages,
        )

    def reached(
        self,
        messages: list[ChatMessage],
    ) -> bool:
        """
        Return True when the approximate token count reaches
        or exceeds the configured threshold.
        """

        return (
            self.count(messages)
            >= self._threshold
        )
