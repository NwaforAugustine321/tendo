
from __future__ import annotations

import logging
from collections.abc import Mapping

import httpx

from .contracts import WebhookEvent
from .interface import WebhookClientInterface


logger = logging.getLogger(__name__)


class WebhookConfig:

    def __init__(
        self,
        *,
        url: str,
        secret: str,
        timeout: float = 30.0,
    ) -> None:

        self.url = url
        self.secret = secret
        self.timeout = timeout


class WebhookClient(WebhookClientInterface):

    def __init__(
        self,
        *,
        hooks: Mapping[str, WebhookConfig],
    ) -> None:

        self._hooks = hooks
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:

        if self._client is not None:
            return

        self._client = httpx.AsyncClient()

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

        print('event sending....', event)
        response = await self._client.post(
            webhook.url,
            json=event.model_dump(mode="json"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Webhook-Secret": webhook.secret,
            },
            timeout=webhook.timeout,
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
