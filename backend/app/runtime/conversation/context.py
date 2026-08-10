from __future__ import annotations

from dataclasses import dataclass, field

from app.runtime.chat.message import ChatMessage


@dataclass(slots=True)
class ConversationContext:
    """
    Conversation history available to the current inference.

    This context contains messages that have already been
    retrieved from the conversation store. It does not
    include the messages generated during the current run.
    """

    conversation_id: str | None = None

    messages: list[ChatMessage] = field(
        default_factory=list,
    )

    summary: str | None = None

    metadata: dict[str, object] = field(
        default_factory=dict,
    )

    @property
    def empty(
        self,
    ) -> bool:
        """
        Whether the conversation contains any history.
        """

        return len(self.messages) == 0
