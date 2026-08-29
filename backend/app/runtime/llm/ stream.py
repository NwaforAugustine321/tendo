from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Generic, TypeVar

from .events import LLMEvent
from .response import LLMResponse

T = TypeVar("T")


class LLMStream(Generic[T], ABC):
    """
    Represents one active model generation.

    A stream owns the complete lifecycle of a
    single LLM inference.

    Providers may stream:

    - tokens
    - reasoning
    - tool calls
    - metadata
    - usage
    - errors

    Every provider eventually produces one
    normalized LLMResponse.
    """

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[LLMEvent[T]]:
        ...

    @abstractmethod
    async def __anext__(self) -> LLMEvent[T]:
        ...

    @abstractmethod
    async def final_response(
        self,
    ) -> LLMResponse[T]:
        """
        Wait until generation completes and
        return the normalized response.
        """
        ...

    @abstractmethod
    async def aclose(
        self,
    ) -> None:
        """
        Cancel generation.
        """
        ...