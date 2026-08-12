from __future__ import annotations

from collections.abc import AsyncIterator

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
        max_context_tokens=128000,
        max_output_tokens=4096,
    ) -> None:

        self._max_context_tokens = max_context_tokens
        self._max_output_tokens = max_output_tokens
        self._base_model = model
        self._model = model

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
            print('max toke for this model >>>>>>>>><<<<<<',
                  self._model.max_tokens)
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
    ) -> int:
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
        Prepare the model for one inference.
        """

        model = self._base_model

        #
        # Bind tools.
        #
        if not tool_context.is_empty():

            model = model.bind_tools(
                to_langchain_tools(
                    tool_context.proxy.tools,
                )
            )

        #
        # Bind structured output.
        #
        if (
            output_type is not None
            and self.supports_structured_output
        ):

            model = model.with_structured_output(
                output_type,
            )

        self._model = model

    async def invoke(
        self,
        messages: list[ChatMessage],
    ) -> AIMessage:

        return await self._model.ainvoke(
            self.to_provider_messages(
                messages,
            )
        )

    async def stream(
        self,
        messages: list[ChatMessage],
    ) -> AsyncIterator[AIMessageChunk]:
        """
        Stream chunks from the provider.
        """

        async for chunk in self._model.astream(
            self.to_provider_messages(
                messages,
            )
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

        # Deduplicate list fields in additional_kwargs
        # that get repeated per-chunk during streaming.
        additional = merged.additional_kwargs or {}
        for key, value in additional.items():
            if isinstance(value, list):
                additional[key] = list(dict.fromkeys(value))

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
                        )
                    )

                case "user":

                    result.append(
                        HumanMessage(
                            content=message.content,
                        )
                    )

                case "assistant":

                    result.append(
                        AIMessage(
                            content=message.content,
                        )
                    )

                case "tool":

                    result.append(
                        ToolMessage(
                            content=message.content,
                            tool_call_id=message.tool_call_id,
                        )
                    )

                case _:

                    raise ValueError(
                        f"Unknown role '{message.role}'."
                    )

        return result
