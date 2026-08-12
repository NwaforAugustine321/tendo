from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, TYPE_CHECKING

from app.runtime.agents.run_context import RunContext
from app.runtime.chat.context import ChatContext
from app.runtime.chat.message import ChatMessage
from app.runtime.context_manager.token_counter import (
    TokenCounter,
)
from app.runtime.structured_output.parser import (
    ResponseParser,
)
from app.runtime.toolsets.tool_context import (
    ToolContext,
)

if TYPE_CHECKING:
    from app.runtime.llm.inference_stream import (
        InferenceStream,
    )


class LLM(ABC):
    """
    Base interface implemented by every LLM provider.

    Besides inference, every provider exposes its model
    capabilities so the runtime can manage prompt size
    before making a request.
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

    @property
    @abstractmethod
    def max_context_tokens(
        self,
    ) -> int | None:
        """
        Maximum context window supported by the model.

        Return None if the provider does not expose it.
        """
        ...

    @property
    @abstractmethod
    def max_output_tokens(
        self,
    ) -> int:
        """
        Maximum number of output tokens reserved for
        one generation.
        """
        ...

    @property
    @abstractmethod
    def token_counter(
        self,
    ) -> TokenCounter:
        """
        Token counter used by the ContextManager.

        Providers should return an implementation that
        matches their tokenizer. If unavailable, return
        an estimated token counter.
        """
        ...

    @abstractmethod
    def to_provider_messages(
        self,
        messages: list[ChatMessage],
    ) -> list[Any]:
        """
        Convert ChatMessages to the provider's native message format.
        """
        ...

    @abstractmethod
    def chat(
        self,
        conversation_context: ChatContext,
        run_context: RunContext,
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

    @abstractmethod
    def to_provider_messages(
        self,
        messages: list[ChatMessage],
    ) -> list[Any]:
        ...
