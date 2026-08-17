from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

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

    The provider is prepared for the current Agent configuration
    before inference begins.

    Preparation may configure:

    - native tool binding
    - structured output
    - provider-specific runtime configuration

    Once prepared, the provider can be reused across multiple
    inference iterations within the same Agent configuration.
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
        Convert ChatMessages to the provider's native
        message format.
        """
        ...

    @abstractmethod
    def chat(
        self,
        conversation_context: ChatContext,
        run_context: RunContext,
    ) -> InferenceStream:
        """
        Create an inference stream for the current run.
        """
        ...

    @abstractmethod
    def prepare(
        self,
        *,
        tool_context: ToolContext,
        output_type: type | None,
    ) -> None:
        """
        Prepare the provider for the current Agent configuration.

        Preparation is performed once and reused across
        inference iterations.

        Provider implementations may use this to configure
        native tools, structured output, or other provider-level
        settings.
        """
        ...

    @abstractmethod
    async def invoke(
        self,
        messages: list[ChatMessage],
    ) -> Any:
        """
        Execute one non-streaming inference.
        """
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
    ) -> AsyncIterator[Any]:
        """
        Execute one streaming inference.
        """
        ...

    @abstractmethod
    def merge_chunks(
        self,
        chunks: list[Any],
    ) -> Any:
        """
        Merge provider streaming chunks into one response.
        """
        ...
