from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, TYPE_CHECKING

from app.runtime.chat.context import ChatContext
from app.runtime.chat.message import ChatMessage
from app.runtime.structured_output.parser import ResponseParser
from app.runtime.toolsets.tool_context import ToolContext
from app.runtime.agents.run_context import RunContext

if TYPE_CHECKING:
    from app.runtime.llm.inference_stream import InferenceStream


class LLM(ABC):
    """
    Base interface implemented by every LLM provider.
    """

    @property
    @abstractmethod
    def supports_structured_output(
        self,
    ) -> bool:
        ...

    @property
    @abstractmethod
    def response_parser(
        self,
    ) -> ResponseParser:
        ...

    @abstractmethod
    def chat(
        self,
        ctx: ChatContext,
        run_context: RunContext
    ) -> InferenceStream:
        ...

    @abstractmethod
    def prepare(
        self,
        *,
        tool_context: ToolContext,
        output_type: type | None,
    ) -> None:
        """
        Prepare the provider for one inference.
        """
        ...

    @abstractmethod
    async def invoke(
        self,
        messages: list[ChatMessage],
    ) -> Any:
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
    ) -> AsyncIterator[Any]:
        ...

    @abstractmethod
    def merge_chunks(
        self,
        chunks: list[Any],
    ) -> Any:
        ...
