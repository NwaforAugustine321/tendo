
from __future__ import annotations

from abc import ABC, abstractmethod

from app.contracts import WebhookEvent


class WebhookClientInterface(ABC):

    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send(
        self,
        *,
        hook: str,
        event: WebhookEvent,
    ) -> None:
        raise NotImplementedError
