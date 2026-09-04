from __future__ import annotations

import logging

import httpx

from ..config.settings import settings
from .contracts import WebhookEvent

from .interface import WebhookClientInterface


logger = logging.getLogger(__name__)


class WebhookClient(WebhookClientInterface):

    def __init__(self) -> None:
        self._hooks = settings.webhook.send_hooks
        self._secret = settings.webhook.secret
        self._timeout = settings.webhook.timeout
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is not None:
            return

        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Webhook-Secret": self._secret,
            },
        )

    async def close(self) -> None:
        if self._client is None:
            return

        await self._client.aclose()
        self._client = None

    async def send(
        self,
        *,
        hook: str,
        event: WebhookEvent,
    ) -> None:
        if self._client is None:
            raise RuntimeError(
                "WebhookClient has not been started."
            )

        webhook = self._hooks.get(hook)

        if webhook is None:
            raise ValueError(
                f"Webhook send hook is not configured: {hook}"
            )

        if event.type not in webhook.events:
            raise ValueError(
                f"Webhook event '{event.type}' is not registered "
                f"for send hook '{hook}'."
            )

        response = await self._client.post(
            webhook.url,
            json=event.model_dump(mode="json"),
        )

        response.raise_for_status()

        logger.debug(
            "Webhook event sent",
            extra={
                "hook": hook,
                "type": event.type,
                "event_id": event.event_id,
                "request_id": event.request_id,
            },
        )
