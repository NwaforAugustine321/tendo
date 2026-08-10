from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar
from .response import ToolCall

T = TypeVar("T")


@dataclass(slots=True)
class LLMEvent(ABC, Generic[T]):
    """
    Base class for every event emitted by an LLMStream.

    Provider-specific payloads are stored in `provider_event`.
    """

    provider_event: T | None = None


@dataclass(slots=True)
class GenerationStartedEvent(LLMEvent[T]):
    """
    Fired once generation begins.
    """


@dataclass(slots=True)
class GenerationFinishedEvent(LLMEvent[T]):
    """
    Fired once generation completes.
    """


@dataclass(slots=True)
class TokenEvent(LLMEvent[T]):
    """
    One streamed token/chunk.
    """

    text: str = ""


@dataclass(slots=True)
class TextDeltaEvent(LLMEvent[T]):
    """
    Incremental text update.

    Example

        "Hel"

        "lo "

        "World"
    """

    delta: str = ""


@dataclass(slots=True)
class TextCompletedEvent(LLMEvent[T]):
    """
    Complete generated text.
    """

    text: str = ""


@dataclass(slots=True)
class ToolCallStartedEvent(LLMEvent[T]):
    """
    Model started requesting a tool.
    """

    tool_call: ToolCall | None = None


@dataclass(slots=True)
class ToolCallDeltaEvent(LLMEvent[T]):
    """
    Partial tool-call arguments.
    """

    tool_call_id: str = ""

    delta: str = ""


@dataclass(slots=True)
class ToolCallCompletedEvent(LLMEvent[T]):
    """
    Tool call fully generated.
    """

    tool_call: ToolCall | None = None


@dataclass(slots=True)
class ReasoningEvent(LLMEvent[T]):
    """
    Reasoning content from reasoning-capable models.
    """

    text: str = ""


@dataclass(slots=True)
class UsageEvent(LLMEvent[T]):
    """
    Token usage and billing information.
    """

    usage: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(slots=True)
class MetadataEvent(LLMEvent[T]):
    """
    Arbitrary provider metadata.
    """

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(slots=True)
class ErrorEvent(LLMEvent[T]):
    """
    Stream error.
    """

    error: Exception | None = None


@dataclass(slots=True)
class RawProviderEvent(LLMEvent[T]):
    """
    Unmodified provider event.

    Useful for debugging and advanced integrations.
    """

    event: T | None = None
