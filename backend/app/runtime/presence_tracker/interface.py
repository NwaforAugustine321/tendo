from __future__ import annotations

from typing import Protocol

from .state import PresenceState


class PresenceLLM(Protocol):

    async def generate(
        self,
        *,
        state: PresenceState,
    ) -> str | None:
        ...


class PresenceOutput(Protocol):

    async def deliver(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:
        ...


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
