
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from typing import Protocol

from .contracts import WebhookEvent


logger = logging.getLogger(__name__)


class WebhookHandler(Protocol):

    def __call__(
        self,
        *,
        event: WebhookEvent,
    ) -> Awaitable[None]:
        ...


class WebhookDispatcher:

    def __init__(
        self,
        *,
        handlers: dict[str, WebhookHandler],
        events: set[str],
    ) -> None:

        self._handlers = handlers
        self._events = events

        self._tasks: set[
            asyncio.Task[None]
        ] = set()

    async def dispatch(
        self,
        *,
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

        task = asyncio.create_task(
            self._run_handler(
                handler,
                event,
            ),
        )

        self._tasks.add(task)

        task.add_done_callback(
            self._tasks.discard,
        )

    async def _run_handler(
        self,
        handler: WebhookHandler,
        event: WebhookEvent,
    ) -> None:

        try:
            await handler(
                event=event,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Webhook handler failed",
                extra={
                    "type": event.type,
                    "event_id": event.event_id,
                    "request_id": event.request_id,
                },
            )
