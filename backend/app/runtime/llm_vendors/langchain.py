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
    InferenceMode,
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
    """
    LangChain-backed runtime LLM.

    The provider model is prepared lazily and cached.

    Normal inference:

        tools_enabled=True
            ↓
        tool_search + call_tool bound

    Forced-final inference:

        tools_enabled=False
            ↓
        no tools bound

    Prepared models are cached so that tool binding and structured
    output configuration are not rebuilt for every inference.

    A new prepared model is created only when the preparation
    configuration changes.
    """

    def __init__(
        self,
        model: BaseChatModel,
        *,
        supports_structured_output: bool = True,
        max_context_tokens: int = 128000,
        max_output_tokens: int = 4096,
    ) -> None:

        self._max_context_tokens = (
            max_context_tokens
        )

        self._max_output_tokens = (
            max_output_tokens
        )

        #
        # Never mutate the original provider model.
        #
        self._base_model = model

        #
        # Currently active prepared model.
        #
        self._model = model

        #
        # Cache of prepared models.
        #
        #
        # Key:
        #
        # (
        #     tools_enabled,
        #     tool_signature,
        #     output_type,
        # )
        #
        self._prepared_models: dict[
            tuple[
                bool,
                tuple[str, ...],
                type | None,
            ],
            BaseChatModel,
        ] = {}

        #
        # Current preparation key.
        #
        self._prepared_key: (
            tuple[
                bool,
                tuple[str, ...],
                type | None,
            ]
            | None
        ) = None

        self._prepared = False

        self._supports_structured_output = (
            supports_structured_output
        )

        self._response_parser = (
            ResponseParser()
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def max_output_tokens(
        self,
    ) -> int:
        """
        Maximum number of tokens the model can
        generate in one response.
        """

        max_tokens = getattr(
            self._model,
            "max_tokens",
            None,
        )

        if max_tokens is not None:

            return max_tokens

        return self._max_output_tokens

    @property
    def max_context_tokens(
        self,
    ) -> int:

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

    # ------------------------------------------------------------------
    # Chat / inference
    # ------------------------------------------------------------------

    def chat(
        self,
        *,
        conversation_context: ConversationContext,
        run_context: RunContext,
        mode: InferenceMode = InferenceMode.STREAM,
        tools_enabled: bool = True,
    ) -> InferenceStream:
        """
        Create one inference stream.

        tools_enabled=True
            Normal reasoning/action mode.

        tools_enabled=False
            Forced-final mode with no tools available.
        """

        return InferenceStream(
            agent=run_context.agent,
            conversation_context=conversation_context,
            run_context=run_context,
            mode=mode,
            tools_enabled=tools_enabled,
        )

    # ------------------------------------------------------------------
    # Model preparation
    # ------------------------------------------------------------------

    def prepare(
        self,
        *,
        tool_context: ToolContext,
        output_type: type | None,
        tools_enabled: bool = True,
    ) -> None:
        """
        Prepare the provider model.

        Preparation is cached.

        Normal mode:

            tools_enabled=True
            → bind runtime proxy tools

        Forced-final mode:

            tools_enabled=False
            → bind no tools

        The provider model is rebuilt only when the preparation
        configuration changes.
        """

        #
        # --------------------------------------------------------------
        # Determine runtime tools
        # --------------------------------------------------------------
        #

        if (
            tools_enabled
            and not tool_context.is_empty()
        ):

            proxy_tools = list(
                tool_context.proxy.tools,
            )

        else:

            proxy_tools = []

        #
        # --------------------------------------------------------------
        # Build stable tool signature
        # --------------------------------------------------------------
        #

        tool_signature = tuple(
            sorted(
                self._tool_signature(
                    tool,
                )
                for tool in proxy_tools
            )
        )

        preparation_key = (
            tools_enabled,
            tool_signature,
            output_type,
        )

        #
        # --------------------------------------------------------------
        # Reuse currently active model
        # --------------------------------------------------------------
        #

        if (
            self._prepared
            and self._prepared_key
            == preparation_key
        ):

            return

        #
        # --------------------------------------------------------------
        # Reuse cached model
        # --------------------------------------------------------------
        #

        cached_model = (
            self._prepared_models.get(
                preparation_key,
            )
        )

        if cached_model is not None:

            self._model = cached_model

            self._prepared_key = (
                preparation_key
            )

            self._prepared = True

            return

        #
        # --------------------------------------------------------------
        # Create prepared model
        # --------------------------------------------------------------
        #

        #
        # ALWAYS start from the untouched base model.
        #
        model = self._base_model

        #
        # --------------------------------------------------------------
        # Bind tools only in normal mode
        # --------------------------------------------------------------
        #

        if (
            tools_enabled
            and proxy_tools
        ):

            model = model.bind_tools(
                to_langchain_tools(
                    proxy_tools,
                ),
            )

        #
        # --------------------------------------------------------------
        # Structured output
        # --------------------------------------------------------------
        #

        if (
            output_type is not None
            and self.supports_structured_output
        ):

            model = model.with_structured_output(
                output_type,
            )

        #
        # --------------------------------------------------------------
        # Cache prepared model
        # --------------------------------------------------------------
        #

        self._prepared_models[
            preparation_key
        ] = model

        #
        # Make it the active model.
        #
        self._model = model

        self._prepared_key = (
            preparation_key
        )

        self._prepared = True

    # ------------------------------------------------------------------
    # Tool signature
    # ------------------------------------------------------------------

    @staticmethod
    def _tool_signature(
        tool: Any,
    ) -> str:
        """
        Build a stable signature for a runtime tool.

        The tool name is the primary identifier.

        When schema information is available, include it so that
        a changed runtime tool schema results in a new prepared
        provider model.
        """

        name = getattr(
            tool,
            "name",
            None,
        )

        if not name:

            name = (
                f"{tool.__class__.__module__}."
                f"{tool.__class__.__qualname__}"
            )

        #
        # Try to include the argument schema.
        #
        args_schema = getattr(
            tool,
            "args_schema",
            None,
        )

        schema = ""

        if args_schema is not None:

            try:

                if hasattr(
                    args_schema,
                    "model_json_schema",
                ):

                    schema = str(
                        args_schema.model_json_schema(),
                    )

                elif hasattr(
                    args_schema,
                    "schema",
                ):

                    schema = str(
                        args_schema.schema(),
                    )

                else:

                    schema = str(
                        args_schema,
                    )

            except Exception:

                schema = str(
                    args_schema,
                )

        #
        # Description can also change the effective tool contract.
        #
        description = getattr(
            tool,
            "description",
            "",
        )

        return (
            f"{name}|"
            f"{description}|"
            f"{schema}"
        )

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    async def invoke(
        self,
        messages: list[ChatMessage],
    ) -> AIMessage:
        """
        Invoke the currently prepared provider.
        """

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
        Stream from the currently prepared provider.
        """

        async for chunk in self._model.astream(
            self.to_provider_messages(
                messages,
            ),
        ):

            yield chunk

    # ------------------------------------------------------------------
    # Chunk merging
    # ------------------------------------------------------------------

    def merge_chunks(
        self,
        chunks: list[AIMessageChunk],
    ) -> AIMessage:
        """
        Merge streamed chunks into one AIMessage.
        """

        if not chunks:

            return AIMessage(
                content="",
            )

        merged = chunks[0]

        for chunk in chunks[1:]:

            merged += chunk

        #
        # Deduplicate repeated list fields.
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

    # ------------------------------------------------------------------
    # Provider message conversion
    # ------------------------------------------------------------------

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
