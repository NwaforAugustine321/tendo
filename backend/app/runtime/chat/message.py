from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.runtime.llm.response import LLMResponse, ToolCall


@dataclass(slots=True, frozen=True)
class ChatMessage:
    """
    One message in a conversation.
    """

    role: str

    content: str | list[Any]

    name: str | None = None

    tool_call_id: str | None = None

    tool_calls: list[ToolCall] = field(
        default_factory=list,
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    created_at: datetime = field(
        default_factory=datetime.utcnow,
    )

    @classmethod
    def system(
        cls,
        content: str,
    ) -> ChatMessage:

        return cls(
            role="system",
            content=content,
        )

    @classmethod
    def user(
        cls,
        content: str,
    ) -> ChatMessage:

        return cls(
            role="user",
            content=content,
        )

    @classmethod
    def assistant(
        cls,
        content: str = "",
        *,
        tool_calls: list[ToolCall] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:

        return cls(
            role="assistant",
            content=content,
            tool_calls=tool_calls or [],
            metadata=metadata or {},
        )

    @classmethod
    def tool(
        cls,
        *,
        tool_call_id: str,
        name: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:

        return cls(
            role="tool",
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            metadata=metadata or {},
        )

    @classmethod
    def from_llm_response(
        cls,
        response: LLMResponse,
    ) -> ChatMessage:
        """
        Convert an LLMResponse into a ChatMessage
        """

        return cls.assistant(
            content=response.text,
            tool_calls=response.tool_calls,
            metadata=response.metadata,
        )
