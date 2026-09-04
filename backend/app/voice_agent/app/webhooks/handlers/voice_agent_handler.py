from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from ...webhooks.contracts import WebhookEvent
from ...webhooks.contracts import (
    WebhookType,
    HOOKS
)


logger = logging.getLogger(__name__)


class VoiceCommandHandlers:

    def __init__(
        self,
        *,
        speak: Callable[[str], Awaitable[None]],
    ) -> None:
        self._speak = speak

    async def handle(
        self,
        *,
        event: WebhookEvent,
    ) -> None:

        if event.type not in {
            WebhookType.VOICE_PRESENCE,
            WebhookType.VOICE_RESPONSE,
        }:
            return

        text = event.payload.get("text")

        if not isinstance(text, str) or not text.strip():
            logger.warning(
                "[VoiceCommandHandlers] Missing text: event_id=%s",
                event.event_id,
            )
            return

        logger.info(
            "[VoiceCommandHandlers] Speaking: "
            "event_id=%s type=%s",
            event.event_id,
            event.type,
        )

        await self._speak(text.strip())
