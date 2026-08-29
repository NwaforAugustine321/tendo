from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar


T = TypeVar("T")


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
    """
    Provider-independent LLM response.

    T is the provider's raw response type.
    """

    text: str = ""
    output: T | None = None

    tool_calls: list[ToolCall] = field(
        default_factory=list,
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    raw: T | None = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @property
    def is_final(self) -> bool:
        return not self.tool_calls

    def tool_to_chat_message(
        self,
    ) -> ChatMessage:

        return ChatMessage.assistant(
            content=self.text,
            tool_calls=self.tool_calls,
            metadata=self.metadata,
        )
