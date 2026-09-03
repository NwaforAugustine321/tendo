
from __future__ import annotations

from typing import Iterable, Protocol

from .state import PresenceState


class PresenceLLM(Protocol):

    async def generate(
        self,
        *,
        state: PresenceState,
    ) -> str | None:
        ...


class PresenceConsumer(Protocol):

    async def send(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:
        ...


class PresenceOutput(Protocol):

    async def deliver(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:
        ...


class PresenceOutputDispatcher:

    def __init__(
        self,
        *,
        consumers: Iterable[PresenceConsumer],
    ) -> None:
        self._consumers = list(
            consumers,
        )

    async def deliver(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:
        for consumer in self._consumers:
            try:
                await consumer.send(
                    text=text,
                    generation=generation,
                )

            except Exception:
                # One consumer must never prevent the remaining
                # consumers from receiving the presence output.
                continue


class PresenceTrackerInterface(Protocol):

    def start(
        self,
        *,
        user_request: str,
    ) -> None:
        ...

    def update(
        self,
        *,
        state: PresenceState,
    ) -> None:
        ...

    def notify_user_activity(
        self,
    ) -> None:
        ...

    def notify_state_event(
        self,
        *,
        state: PresenceState | None = None,
    ) -> None:
        ...

    def stop(
        self,
    ) -> None:
        ...

    async def aclose(
        self,
    ) -> None:
        ...
