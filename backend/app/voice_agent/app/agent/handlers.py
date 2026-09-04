
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from livekit.agents import (
    AgentSession,
    ErrorEvent,
    stt,
    tts,
)

from ..webhooks.contracts import WebhookEvent
from ..webhooks.client import WebhookClientInterface


logger = logging.getLogger(__name__)


class VoiceSessionHandlers:

    def __init__(
        self,
        *,
        webhook_client: WebhookClientInterface,
        session_id: str,
    ) -> None:

        self._webhook_client = webhook_client
        self._session_id = session_id

    def register(
        self,
        session: AgentSession,
        resources: Any = None,
    ) -> None:

        @session.on("user_input_transcribed")
        def on_user_input_transcribed(
            event: Any,
        ) -> None:

            if not event.is_final:
                return

            transcript = event.transcript

            if not transcript:
                return

            webhook_event = WebhookEvent(
                type="voice.transcript",
                event_id=str(uuid4()),
                request_id=str(uuid4()),
                payload={
                    "session_id": self._session_id,
                    "text": transcript,
                },
            )

            asyncio.create_task(
                self._send_transcript(
                    webhook_event,
                ),
            )

        @session.on("error")
        def on_error(
            ev: ErrorEvent,
        ) -> None:

            error = ev.error
            source = ev.source

            logger.error(
                "[VoiceSessionHandlers] AgentSession error: "
                "source=%s recoverable=%s error=%s",
                type(source).__name__,
                error.recoverable,
                error,
            )

            if error.recoverable:
                return

            if isinstance(
                source,
                tts.TTS,
            ):
                logger.warning(
                    "[VoiceSessionHandlers] Recovering from TTS error.",
                )

                error.recoverable = True

                return

            if isinstance(
                source,
                stt.STT,
            ):
                logger.warning(
                    "[VoiceSessionHandlers] "
                    "STT error detected. Creating fresh STT instance.",
                )

                try:

                    if resources is not None:

                        get_stt = getattr(
                            resources,
                            "get_stt",
                            None,
                        )

                        if callable(get_stt):
                            session._stt = get_stt()

                    error.recoverable = True

                    logger.info(
                        "[VoiceSessionHandlers] "
                        "STT recovered with fresh instance.",
                    )

                except Exception:

                    logger.exception(
                        "[VoiceSessionHandlers] "
                        "Failed to recover STT.",
                    )

                return

            logger.error(
                "[VoiceSessionHandlers] "
                "Unhandled unrecoverable error: "
                "source=%s error=%s",
                type(source).__name__,
                error,
            )

        @session.on("close")
        def on_close(
            *args: Any,
        ) -> None:

            logger.info(
                "[VoiceSessionHandlers] AgentSession closed: "
                "session_id=%s",
                self._session_id,
            )

    async def _send_transcript(
        self,
        event: WebhookEvent,
    ) -> None:

        try:

            await self._webhook_client.send(
                hook="main_app",
                event=event,
            )

        except Exception:

            logger.exception(
                "[VoiceSessionHandlers] "
                "Failed to send transcript webhook: "
                "session_id=%s event_id=%s",
                self._session_id,
                event.event_id,
            )
