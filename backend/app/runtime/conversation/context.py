from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.runtime.chat.message import ChatMessage


class ConversationState(str, Enum):
    """
    Current lifecycle state of the loaded conversation.
    """

    ACTIVE = "active"

    SUMMARIZING = "summarizing"

    SUMMARIZED = "summarized"


@dataclass(slots=True)
class ConversationContext:
    """
    Conversation history available to the current inference.

    This is a runtime object assembled by the
    ConversationProvider from the persisted
    conversation record and conversation messages.

    It contains only the information required to
    build the prompt. It does not include messages
    generated during the current execution.
    """

    conversation_id: str | None = None

    summary: str | None = None

    messages: list[ChatMessage] = field(
        default_factory=list,
    )

    state: ConversationState = (
        ConversationState.ACTIVE
    )

    metadata: dict[str, object] = field(
        default_factory=dict,
    )

    @property
    def empty(
        self,
    ) -> bool:
        """
        Whether the conversation contains any
        persisted history.
        """

        return (
            not self.summary
            and not self.messages
        )

    @property
    def has_summary(
        self,
    ) -> bool:
        """
        Whether the conversation includes
        a persisted summary.
        """

        return bool(
            self.summary,
        )
