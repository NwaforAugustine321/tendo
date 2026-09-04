from __future__ import annotations

from typing import Protocol
from enum import Enum, StrEnum


class ResponseConsumer(Protocol):

    async def send(
        self,
        *,
        text: str,
        kind: str,
        sequence: int,
    ) -> None:
        ...

    async def interrupt(self) -> None:
        ...


class ResponseQueueInterface(Protocol):

    async def submit(
        self,
        *,
        text: str,
        kind: str,
    ) -> None:
        ...

    async def deliver(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:
        ...

    async def aclose(self) -> None:
        ...


class Kind(StrEnum):
    RESPONSE = "response"

    PRESENCE_STATE = "presence_state"
