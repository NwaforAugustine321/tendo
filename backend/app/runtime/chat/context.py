from __future__ import annotations

from dataclasses import dataclass, field

from .message import ChatMessage


@dataclass(slots=True)
class ChatContext:
    """
    Conversation history.
    """

    messages: list[ChatMessage] = field(
        default_factory=list,
    )

    def add(
        self,
        message: ChatMessage,
    ) -> None:
        self.messages.append(
            message,
        )

    def extend(
        self,
        messages: list[ChatMessage],
    ) -> None:
        self.messages.extend(
            messages,
        )

    def pop(
        self,
    ) -> ChatMessage:
        return self.messages.pop()

    @property
    def last(
        self,
    ) -> ChatMessage | None:
        if not self.messages:
            return None

        return self.messages[-1]

    def clear(
        self,
    ) -> None:
        self.messages.clear()
