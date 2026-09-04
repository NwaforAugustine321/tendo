
from __future__ import annotations

from collections.abc import Awaitable
from typing import Protocol

from app.config.settings import settings
from .contracts import WebhookEvent


class WebhookHandler(Protocol):

    def __call__(
        self,
        event: WebhookEvent,
    ) -> Awaitable[None]:
        ...


class WebhookDispatcher:

    def __init__(
        self,
        *,
        handlers: dict[str, WebhookHandler],
    ) -> None:

        self._handlers = handlers

        self._events = set().union(
            *(
                hook.events
                for hook in settings.webhook.receive_hooks.values()
            )
        )

    async def dispatch(
        self,
        event: WebhookEvent,
    ) -> None:

        if event.type not in self._events:

            raise ValueError(
                f"Webhook event is not registered for receiving: "
                f"{event.type}"
            )

        handler = self._handlers.get(
            event.type,
        )

        if handler is None:

            raise ValueError(
                f"No handler registered for webhook event: "
                f"{event.type}"
            )

        await handler(
            event,
        )
