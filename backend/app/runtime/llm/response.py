from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar


T = TypeVar("T")


class LLMAction(str, Enum):
    FINAL = "final"
    CONTINUE = "continue"
    REQUEST_USER_INPUT = "request_user_input"


class InteractionType(str, Enum):
    USER_INPUT = "user_input"


@dataclass(slots=True)
class Interaction:
    """
    Describes an interaction requested from the user.
    """

    type: InteractionType


@dataclass(slots=True)
class ToolCall:
    """
    One tool requested by the LLM.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMResponse(Generic[T]):

    text: str = ""
    content: str | None = None
    question: str | None = None

    output: T | None = None

    tool_calls: list[ToolCall] = field(
        default_factory=list,
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    raw: T | None = None

    action: LLMAction | None = None
    interaction: Interaction | None = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @property
    def is_final(self) -> bool:
        return (
            not self.has_tool_calls
            and (
                self.action is None
                or self.action == LLMAction.FINAL
            )
        )

    @property
    def should_continue(self) -> bool:
        return self.action == LLMAction.CONTINUE

    @property
    def requests_user_input(self) -> bool:
        return (
            self.action
            == LLMAction.REQUEST_USER_INPUT
        )

    def tool_to_chat_message(
        self,
    ) -> ChatMessage:

        return ChatMessage.assistant(
            content=self.text,
            tool_calls=self.tool_calls,
            metadata=self.metadata,
        )
