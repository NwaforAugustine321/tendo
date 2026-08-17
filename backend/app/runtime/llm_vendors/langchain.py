from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.runtime.agents.run_context import RunContext
from app.runtime.chat.message import ChatMessage
from app.runtime.conversation.context import (
    ConversationContext,
)
from app.runtime.llm.inference_stream import (
    InferenceStream,
)
from app.runtime.llm.llm import LLM
from app.runtime.structured_output.parser import (
    ResponseParser,
)
from app.runtime.toolsets.tool_context import (
    ToolContext,
)
from app.runtime.toolsets.utils import (
    to_langchain_tools,
)

from app.runtime.context_manager.estimated_token_counter import (
    EstimatedTokenCounter,
)


class LangChainLLM(LLM):

    def __init__(
        self,
        model: BaseChatModel,
        *,
        supports_structured_output: bool = True,
        max_context_tokens: int = 128000,
        max_output_tokens: int = 4096,
    ) -> None:

        self._max_context_tokens = max_context_tokens
        self._max_output_tokens = max_output_tokens

        #
        # Keep the original provider model untouched.
        #
        self._base_model = model

        #
        # Model actually used for inference.
        #
        self._model = model

        #
        # Preparation state.
        #
        self._prepared = False
        self._prepared_output_type: type | None = None

        self._supports_structured_output = (
            supports_structured_output
        )

        self._response_parser = ResponseParser()

    @property
    def max_output_tokens(
        self,
    ) -> int:
        """
        Maximum number of tokens the model can
        generate in one response.
        """

        if self._model.max_tokens is not None:

            return self._model.max_tokens

        return self._max_output_tokens

    @property
    def max_context_tokens(
        self,
    ) -> int:
        """
        Maximum context window supported by
        the model.
        """

        return self._max_context_tokens

    @property
    def token_counter(
        self,
    ) -> EstimatedTokenCounter:

        return EstimatedTokenCounter()

    @property
    def response_parser(
        self,
    ) -> ResponseParser:

        return self._response_parser

    @property
    def supports_structured_output(
        self,
    ) -> bool:

        return self._supports_structured_output

    @property
    def model(
        self,
    ) -> BaseChatModel:

        return self._model

    @property
    def prepared(
        self,
    ) -> bool:

        return self._prepared

    def chat(
        self,
        *,
        conversation_context: ConversationContext,
        run_context: RunContext,
    ) -> InferenceStream:

        return InferenceStream(
            agent=run_context.agent,
            conversation_context=conversation_context,
            run_context=run_context,
        )

    def prepare(
        self,
        *,
        tool_context: ToolContext,
        output_type: type | None,
    ) -> None:
        """
        Prepare the provider once for the current Agent configuration.

        Tool binding and structured-output configuration are performed
        only once. Subsequent calls reuse the already prepared model.
        """

        #
        # Already prepared with the same output configuration.
        #
        if (
            self._prepared
            and self._prepared_output_type is output_type
        ):

            return

        #
        # Start from the original provider model.
        #
        model = self._base_model

        #
        # Bind the runtime proxy tools.
        #
        # The proxy exposes:
        #
        #   - tool_search
        #   - call_tool
        #
        # The discovered tools remain behind the proxy and are not
        # directly bound to the LLM.
        #
        if not tool_context.is_empty():

            proxy_tools = (
                tool_context.proxy.tools
            )

            if proxy_tools:

                model = model.bind_tools(
                    to_langchain_tools(
                        proxy_tools,
                    ),
                )

        #
        # Bind structured output when requested.
        #
        if (
            output_type is not None
            and self.supports_structured_output
        ):

            model = model.with_structured_output(
                output_type,
            )

        #
        # Store the prepared provider.
        #
        self._model = model

        self._prepared_output_type = (
            output_type
        )

        self._prepared = True

    async def invoke(
        self,
        messages: list[ChatMessage],
    ) -> AIMessage:

        return await self._model.ainvoke(
            self.to_provider_messages(
                messages,
            ),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
    ) -> AsyncIterator[AIMessageChunk]:
        """
        Stream chunks from the prepared provider.
        """

        async for chunk in self._model.astream(
            self.to_provider_messages(
                messages,
            ),
        ):

            yield chunk

    def merge_chunks(
        self,
        chunks: list[AIMessageChunk],
    ) -> AIMessage:
        """
        Merge streamed chunks into a single AIMessage.
        """

        if not chunks:

            return AIMessage(
                content="",
            )

        merged = chunks[0]

        for chunk in chunks[1:]:

            merged += chunk

        #
        # Deduplicate list fields in additional_kwargs
        # that may be repeated across streamed chunks.
        #
        additional = (
            merged.additional_kwargs
            or {}
        )

        for key, value in additional.items():

            if isinstance(
                value,
                list,
            ):

                additional[key] = list(
                    dict.fromkeys(
                        value,
                    ),
                )

        return merged

    def to_provider_messages(
        self,
        messages: list[ChatMessage],
    ) -> list[BaseMessage]:

        result: list[BaseMessage] = []

        for message in messages:

            match message.role:

                case "system":

                    result.append(
                        SystemMessage(
                            content=message.content,
                        ),
                    )

                case "user":

                    result.append(
                        HumanMessage(
                            content=message.content,
                        ),
                    )

                case "assistant":

                    result.append(
                        AIMessage(
                            content=message.content,
                        ),
                    )

                case "tool":

                    result.append(
                        ToolMessage(
                            content=message.content,
                            tool_call_id=(
                                message.tool_call_id
                            ),
                        ),
                    )

                case _:

                    pass

        return result
