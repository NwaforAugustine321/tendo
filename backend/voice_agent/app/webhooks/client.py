
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
            logger.warning(
                "Webhook client is not started: "
                "hook=%s type=%s event_id=%s request_id=%s",
                hook,
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        webhook = self._hooks.get(hook)

        if webhook is None:
            logger.error(
                "Webhook hook is not configured: "
                "hook=%s type=%s event_id=%s request_id=%s",
                hook,
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        try:
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

        except httpx.TimeoutException:
            logger.warning(
                "Webhook request timed out: "
                "hook=%s url=%s type=%s event_id=%s request_id=%s",
                hook,
                webhook.url,
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Webhook request returned HTTP error: "
                "hook=%s url=%s status=%s type=%s "
                "event_id=%s request_id=%s",
                hook,
                webhook.url,
                exc.response.status_code,
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        except httpx.RequestError as exc:
            logger.warning(
                "Webhook request failed: "
                "hook=%s url=%s type=%s event_id=%s "
                "request_id=%s error=%s",
                hook,
                webhook.url,
                event.type,
                event.event_id,
                event.request_id,
                exc,
            )
            return

        except Exception:
            logger.exception(
                "Unexpected webhook delivery failure: "
                "hook=%s url=%s type=%s event_id=%s request_id=%s",
                hook,
                webhook.url,
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        logger.debug(
            "Webhook event acknowledged: "
            "hook=%s status=%s type=%s event_id=%s request_id=%s",
            hook,
            response.status_code,
            event.type,
            event.event_id,
            event.request_id,
        )
