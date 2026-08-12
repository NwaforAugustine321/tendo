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

    @classmethod
    def from_provider_messages(
        cls,
        messages: list,
    ) -> list[ChatMessage]:
        """
        Convert a list of provider message
        back to ChatMessage objects.
        """

        result = []
        for msg in messages:

            role = msg["role"]
            content = msg["content"]
            metadata = msg.get("metadata", {})

            if role == "system":
                result.append(cls.system(content))
            elif role == "user":
                result.append(cls.user(content))
            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                result.append(
                    cls.assistant(
                        content,
                        metadata=metadata,
                        tool_calls=tool_calls
                    )
                )
            elif role == "tool":
                result.append(cls.tool(
                    tool_call_id=msg.get("tool_call_id", ""),
                    name=msg.get("name", ""),
                    content=content,
                    metadata=metadata
                ))
        return result

    @staticmethod
    def to_dicts(
        messages: list[ChatMessage],
    ) -> list[dict[str, str]]:
        """
        Convert a list of ChatMessages to plain
        [{role, content}] dicts for storage.

        Skips tool messages and empty content.
        """

        results = []

        for msg in messages:

            role = str(
                getattr(msg.role, "value", msg.role)
            )

            if role == "tool":
                continue

            content = msg.content

            if not content:
                continue

            if not isinstance(content, str):
                content = str(content)

            results.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return results

    @classmethod
    def from_dicts(
        cls,
        dicts: list[dict[str, str]],
    ) -> list[ChatMessage]:
        """
        Convert a list of [{role, content}] dicts
        back to ChatMessage objects.
        """

        return [
            cls(
                role=d["role"],
                content=d["content"],
            )
            for d in dicts
            if d.get("content")
        ]

    @staticmethod
    def to_text(
        messages: list["ChatMessage"],
    ) -> str:
        """
        Convert messages into a plain-text transcript.

        Tool messages and empty messages are skipped.
        """

        lines: list[str] = []

        for message in ChatMessage.to_dicts(
            messages,
        ):

            lines.append(
                f"{message['role']}: "
                f"{message['content']}"
            )

        return "\n".join(lines)
