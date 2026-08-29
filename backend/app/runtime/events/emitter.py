from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any


Callback = Callable[
    [Any],
    Awaitable[None] | None,
]


class Emitter(ABC):
    """
    Event emitter interface.

    Events are identified by a string name and
    may have multiple callbacks registered for them.
    """

    @abstractmethod
    def on(
        self,
        event: str,
        callbacks: list[Callback],
    ) -> None:
        """
        Register callbacks for an event.
        """
        ...

    @abstractmethod
    def off(
        self,
        event: str,
        callbacks: list[Callback],
    ) -> None:
        """
        Remove callbacks from an event.
        """
        ...

    @abstractmethod
    async def emit(
        self,
        event: str,
        payload: Any = None,
    ) -> None:
        """
        Emit an event to all callbacks registered
        for that specific event.
        """
        ...
