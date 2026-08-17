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
        InferenceMode,
        InferenceStream,
    )


class LLM(ABC):
    """
    Base interface implemented by every LLM provider.

    The provider can maintain multiple prepared configurations.

    Normal inference:

        tools_enabled=True
            ↓
        prepared model with runtime tools

    Forced-final inference:

        tools_enabled=False
            ↓
        prepared model without runtime tools

    Provider implementations are responsible for caching and
    reusing prepared models when the configuration has not changed.
    """

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

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

        Providers should return an implementation that matches
        their tokenizer. If unavailable, return an estimated
        token counter.
        """
        ...

    # ------------------------------------------------------------------
    # Provider message conversion
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Inference creation
    # ------------------------------------------------------------------

    @abstractmethod
    def chat(
        self,
        *,
        conversation_context: ChatContext,
        run_context: RunContext,
        mode: InferenceMode = ...,  # type: ignore[assignment]
        tools_enabled: bool = True,
    ) -> InferenceStream:
        """
        Create one inference stream.

        tools_enabled=True
            Normal reasoning/action inference. Runtime tools
            may be available.

        tools_enabled=False
            Tool-free inference. Used when the runner requires
            the model to produce a final response without being
            able to call tools.

        The provider should reuse a cached prepared model where
        possible.
        """
        ...

    # ------------------------------------------------------------------
    # Provider preparation
    # ------------------------------------------------------------------

    @abstractmethod
    def prepare(
        self,
        *,
        tool_context: ToolContext,
        output_type: type | None,
        tools_enabled: bool = True,
    ) -> None:
        """
        Prepare the provider for the requested inference mode.

        tools_enabled=True
            Prepare/reuse the normal model with runtime tools.

        tools_enabled=False
            Prepare/reuse a model with no runtime tools.

        Provider implementations should cache prepared configurations
        rather than rebuilding/binding the model on every inference.
        """
        ...

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Response handling
    # ------------------------------------------------------------------

    @abstractmethod
    def merge_chunks(
        self,
        chunks: list[Any],
    ) -> Any:
        """
        Merge provider streaming chunks into one response.
        """
        ...
