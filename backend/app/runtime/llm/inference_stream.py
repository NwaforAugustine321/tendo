from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from enum import Enum
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessageChunk

from app.runtime.agents.run_context import RunContext
from app.runtime.chat.message import ChatMessage
from app.runtime.conversation.context import (
    ConversationContext,
)
from app.runtime.events.events import (
    ErrorEvent,
    GenerationFinishedEvent,
    LLMEvent,
)
from app.runtime.llm.response import LLMResponse
from app.runtime.prompts.builder import PromptBuilder
from app.runtime.prompts.context import PromptContext

if TYPE_CHECKING:
    from app.runtime.agents.agent import Agent


class InferenceMode(str, Enum):
    INVOKE = "invoke"
    STREAM = "stream"


class InferenceStream(AsyncIterator[LLMEvent]):
    """
    Represents one active inference.

    Responsibilities
    ----------------
    - Build the prompt
    - Invoke the model
    - Emit normalized events
    - Build the final LLMResponse

    Context optimization is handled before this stream
    reaches inference by AgentRunner.

    This class does not:

    - count context tokens
    - decide when optimization is required
    - optimize conversations
    """

    def __init__(
        self,
        *,
        agent: Agent,
        conversation_context: ConversationContext,
        run_context: RunContext,
        mode: InferenceMode = InferenceMode.STREAM,
    ) -> None:

        self._agent = agent
        self._conversation_context = conversation_context
        self._run_context = run_context
        self._mode = mode

        self._closed = False
        self._finished = False
        self._error: Exception | None = None

        self._response: LLMResponse | None = None

        self._events: asyncio.Queue[
            LLMEvent | None
        ] = asyncio.Queue()

        self._task = asyncio.create_task(
            self._run(),
        )

    @property
    def finished(
        self,
    ) -> bool:
        return self._finished

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    @property
    def error(
        self,
    ) -> Exception | None:
        return self._error

    @property
    def response(
        self,
    ) -> LLMResponse | None:
        return self._response

    def __aiter__(
        self,
    ) -> AsyncIterator[LLMEvent]:
        return self

    async def __anext__(
        self,
    ) -> LLMEvent:

        if self._closed:
            raise StopAsyncIteration

        event = await self._events.get()

        if event is None:
            self._closed = True
            raise StopAsyncIteration

        return event

    async def _run(
        self,
    ) -> None:

        try:

            #
            # Build the prompt using the PromptState
            # owned by the current AgentSession.
            #
            builder = PromptBuilder(
                context=PromptContext(
                    agent=self._agent,
                    run_context=self._run_context,
                    conversation_context=(
                        self._conversation_context
                    ),
                    prompt_state=(
                        self._run_context.session.prompt_state
                    ),
                ),
            )

            #
            # PromptBuilder builds the actual prompt.
            #
            # No token counting or optimization happens here.
            #
            messages = await (
                self._agent.context_manager.build(
                    builder,
                )
            )

            #
            # Prepare the LLM.
            #
            self._agent.llm.prepare(
                tool_context=self._agent.tool_context,
                output_type=self._agent.output_type,
            )

            #
            # Execute inference.
            #
            provider_response = await self._invoke(
                messages,
            )

            #
            # Parse the final response.
            #
            self._response = (
                self._agent.llm.response_parser.parse(
                    provider_response=provider_response,
                    output_type=self._agent.output_type,
                )
            )

            await self._finish()

        except Exception as error:

            await self._handle_error(
                error,
            )

    async def _invoke(
        self,
        messages: list[ChatMessage],
    ) -> Any:

        if self._mode is InferenceMode.STREAM:

            return await self._invoke_stream(
                messages,
            )

        return await self._invoke_once(
            messages,
        )

    async def _invoke_once(
        self,
        messages: list[ChatMessage],
    ) -> Any:

        return await self._agent.llm.invoke(
            messages,
        )

    async def _invoke_stream(
        self,
        messages: list[ChatMessage],
    ) -> Any:

        chunks: list[AIMessageChunk] = []

        async for chunk in self._agent.llm.stream(
            messages,
        ):

            chunks.append(
                chunk,
            )

            await self._emit_chunk(
                chunk,
            )

        return self._agent.llm.merge_chunks(
            chunks,
        )

    async def _emit(
        self,
        event: LLMEvent,
    ) -> None:

        if self._closed:
            return

        await self._events.put(
            event,
        )

    async def _emit_chunk(
        self,
        chunk: AIMessageChunk,
    ) -> None:
        """
        Placeholder for future token streaming events.
        """

        return

    async def _finish(
        self,
    ) -> None:

        if self._finished:
            return

        self._finished = True

        await self._emit(
            GenerationFinishedEvent(),
        )

        await self._events.put(
            None,
        )

    async def _handle_error(
        self,
        error: Exception,
    ) -> None:

        self._error = error

        await self._emit(
            ErrorEvent(
                error=error,
            ),
        )

        await self._finish()

    async def final_response(
        self,
    ) -> LLMResponse:

        await self._task

        if self._error is not None:
            raise self._error

        if self._response is None:
            raise RuntimeError(
                "Inference completed without a response.",
            )

        return self._response

    async def aclose(
        self,
    ) -> None:

        if self._closed:
            return

        self._closed = True

        if not self._task.done():

            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

        while True:

            try:
                self._events.get_nowait()
            except asyncio.QueueEmpty:
                break

        await self._events.put(
            None,
        )
