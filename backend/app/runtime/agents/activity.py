from __future__ import annotations

from collections.abc import AsyncIterator

from app.runtime.events.events import LLMEvent
from app.runtime.llm.inference_stream import InferenceStream
from app.runtime.llm.response import LLMResponse


class AgentActivity(AsyncIterator[LLMEvent]):
    """
    Represents a single execution of an Agent.

    An activity owns exactly one inference.

    Responsibilities
    ----------------
    - Wrap one InferenceStream
    - Expose normalized events
    - Wait for completion
    - Support cancellation
    """

    def __init__(
        self,
        *,
        stream: InferenceStream,
    ) -> None:

        self._stream = stream

    @property
    def stream(self) -> InferenceStream:
        return self._stream

    @property
    def finished(self) -> bool:
        return self._stream.finished

    @property
    def closed(self) -> bool:
        return self._stream.closed

    @property
    def response(self) -> LLMResponse | None:
        return self._stream.response

    @property
    def error(self) -> Exception | None:
        return self._stream.error

    def __aiter__(self) -> AsyncIterator[LLMEvent]:
        return self

    async def __anext__(self) -> LLMEvent:
        return await self._stream.__anext__()

    async def wait(self) -> LLMResponse:
        """
        Wait until the activity completes.
        """
        return await self._stream.final_response()

    async def cancel(self) -> None:
        """
        Cancel the activity.
        """
        await self._stream.aclose()
