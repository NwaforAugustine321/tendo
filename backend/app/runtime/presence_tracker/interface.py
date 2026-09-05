
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .state import PresenceState


class PresencePhase(str, Enum):

    INITIAL = "initial"
    PROGRESS = "progress"


class PresenceAction(str, Enum):

    RESPOND = "respond"
    STATUS = "status"
    HANDOFF = "handoff"


@dataclass(slots=True)
class PresenceResult:

    action: PresenceAction
    message: str | None = None


class PresenceLLM(Protocol):

    async def generate(
        self,
        *,
        state: PresenceState,
        phase: PresencePhase,
    ) -> PresenceResult:
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

    async def classify(
        self,
    ) -> PresenceResult:
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
