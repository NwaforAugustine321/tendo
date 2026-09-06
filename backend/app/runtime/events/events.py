from __future__ import annotations
from typing import Any
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar
from app.runtime.llm.response import ToolCall
from enum import Enum
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


class Status(str, Enum):

    STARTING = (
        "starting_session",
        "Let me see how I can help...",
    )

    UNDERSTANDING = (
        "understanding_request",
        "Let me understand what you're looking for...",
    )

    THINKING = (
        "thinking",
        "Let me think about this for a moment...",
    )

    PLANNING = (
        "planning",
        "I'm working out the best way to approach this...",
    )

    SEARCHING = (
        "searching",
        "Let me look through the available information...",
    )

    READING = (
        "reading",
        "I'm going through the information now...",
    )

    ANALYZING = (
        "analyzing",
        "I'm analyzing what I found...",
    )

    REASONING = (
        "reasoning",
        "Reasoning...",
    )

    RETRIEVING = (
        "retrieving",
        "I'm getting the information I need...",
    )

    SUMMARIZING = (
        "summarizing_context",
        "The conversation is getting long. I'm summarizing the context so I can continue.",
    )

    SUMMARY_COMPLETE = (
        "context_summarized",
        "The conversation context has been summarized. Continuing now.",
    )

    GENERATING = (
        "generating",
        "I'm putting together a response...",
    )

    USING_TOOL = (
        "using_tool",
        "I'm trying to get the information I need...",
    )

    EXECUTING = (
        "executing",
        "I'm working on that now...",
    )

    WAITING = (
        "waiting",
        "I'm waiting for the next step...",
    )

    RETRYING = (
        "retrying",
        "I ran into a small issue, so I'm trying again...",
    )

    FINALIZING = (
        "finalizing",
        "I'm putting the finishing touches together...",
    )

    COMPLETED = (
        "completed",
        "Done. I've finished working on this...",
    )

    FAILED = (
        "failed",
        "I wasn't able to complete that successfully.",
    )

    UNSUCCESSFUL = (
        "unsuccessfull",
        "I’m sorry, I wasn’t able to complete that for you this time."
    )

    MAX_ITERATION = (
        "max_iteration",
        "I've reached the processing limit, so I'm finishing with what I have...",
    )

    CANCELLED = (
        "cancelled",
        "The current task has been cancelled.",
    )

    def __new__(
        cls,
        status: str,
        message: str,
    ):
        obj = str.__new__(
            cls,
            status,
        )

        obj._value_ = status
        obj.status = status
        obj.message = message

        return obj


@dataclass(slots=True)
class StatusEvent:

    status: Status

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    @property
    def message(self) -> str:
        return self.status.message


class EventType(str, Enum):

    STATUS = "status"

    PROGRESS = "progress"

    THINKING = "thinking"

    TEXT = "text"

    LLM = "llm"

    TOOL = "tool"

    MEMORY = "memory"

    RETRIEVAL = "retrieval"

    DOCUMENT = "document"

    ERROR = "error"

    COMPLETED = "completed"
