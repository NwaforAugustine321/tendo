from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator
from typing import Any, TYPE_CHECKING
from app.runtime.chat.context import ChatContext
from app.runtime.llm.events import LLMEvent
from app.runtime.llm.response import LLMResponse
from enum import Enum
from app.runtime.llm.events import ErrorEvent
from app.runtime.llm.events import GenerationFinishedEvent
from app.runtime.llm.response import ToolCall
from app.runtime.prompts.builder import PromptBuilder
from app.runtime.prompts.context import PromptContext
from app.runtime.chat.message import ChatMessage
from app.runtime.agents.run_context import RunContext

if TYPE_CHECKING:
    from app.runtime.agents.agent import Agent


class InferenceMode(str, Enum):
    INVOKE = "invoke"
    STREAM = "stream"


class InferenceStream(AsyncIterator[LLMEvent]):
    """
    Represents one active inference.

    One stream == one model generation.

    Responsibilities
    ----------------
    - Build provider messages
    - Invoke the model
    - Emit normalized events
    - Build the final LLMResponse
    - Support cancellation
    """

    def __init__(
        self,
        *,
        agent: Agent,
        chat_context: ChatContext,
        run_context: RunContext,
        mode: InferenceMode = InferenceMode.STREAM,
    ) -> None:

        self._mode = mode
        self._chat_context = chat_context
        self._closed = False
        self._error: Exception | None = None
        self._finished = False

        self._agent = agent
        self._run_context = run_context

        self._events: asyncio.Queue[
            LLMEvent | None
        ] = asyncio.Queue()

        self._response: LLMResponse | None = None

        self._task = asyncio.create_task(
            self._run(),
        )

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def error(
        self,
    ) -> Exception | None:
        return self._error

    @property
    def task(
        self,
    ) -> asyncio.Task:
        return self._task

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
        """
        Execute one inference.

        This owns the entire inference lifecycle.
        """

        try:

            builder = PromptBuilder(
                context=PromptContext(
                    agent=self._agent,
                    run_context=self._run_context,
                    chat_context=self._chat_context,
                ),
            )

            messages = builder.build()

            self._agent.llm.prepare(
                tool_context=self._agent.tool_context,
                output_type=getattr(self._agent, "output_type", None),
            )

            provider_response = await self._invoke(
                messages,
            )

            self._response = (
                self._agent.llm.response_parser.parse(
                    provider_response=provider_response,
                    output_type=getattr(self._agent, "output_type", None),
                )
            )

            await self._finish()

        except Exception as e:

            await self._handle_error(e)

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
        """
        One-shot inference.
        """

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
            chunks.append(chunk)

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
        """
        Push an event to subscribers.
        """

        if self._closed:
            return

        await self._events.put(event)

    async def _emit_chunk(
        self,
        chunk: AIMessageChunk,
    ) -> None:
        """
        Emit events for a streamed chunk.

        Placeholder for future token events.
        """

        return

    async def _finish(
        self,
    ) -> None:
        """
        Mark the inference as complete.
        """

        if self._finished:
            return

        self._finished = True

        await self._emit(
            GenerationFinishedEvent()
        )

        await self._events.put(None)

    async def _handle_error(
        self,
        error: Exception,
    ) -> None:
        """
        Handle inference failure.
        """

        await self._emit(
            ErrorEvent(
                error=error,
            )
        )

        self._error = error
        await self._finish()

    async def final_response(
        self,
    ) -> LLMResponse:
        """
        Wait for inference completion and return
        the normalized response.
        """
        await self._task

        if self._error is not None:
            raise self._error

        if self._response is None:
            raise RuntimeError(
                "Inference completed without a response."
            )

        return self._response

    async def aclose(self):

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

        await self._events.put(None)
