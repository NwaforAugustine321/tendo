
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from livekit.agents import (
    AgentSession,
    AgentStateChangedEvent,
    ErrorEvent,
    get_job_context,
    stt,
    tts,
)
from livekit.protocol import agent as agent_protocol

from ..webhooks.client import WebhookClientInterface
from ..webhooks.contracts import (
    HOOKS,
    WebhookEvent,
    WebhookType,
)
from ..services.voice_agent_service import voice_agent_service

logger = logging.getLogger(__name__)


class VoiceSessionHandlers:

    def __init__(
        self,
        *,
        webhook_client: WebhookClientInterface,
        session_id: str,
        user_id: str,
        business_id: str,
        room: str,
    ) -> None:

        self._webhook_client = webhook_client
        self._session_id = session_id
        self._user_id = user_id
        self._business_id = business_id
        self._room = room
        self._agent_identity = (
            get_job_context()
            .room
            .local_participant
            .identity
        )
        self._background_tasks: set[asyncio.Task] = set()

    def _run_background_task(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def register(
        self,
        session: AgentSession,
        resources: Any = None,
    ) -> None:

        @session.on("agent_state_changed")
        def on_agent_state_changed(
            ev: AgentStateChangedEvent,
        ) -> None:

            self._run_background_task(
                self._update_runtime_state(
                    agent_state=ev.new_state,
                    session_status=agent_protocol.JobStatus.JS_RUNNING,
                ),
            )

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
                type=WebhookType.VOICE_TRANSCRIPT,
                event_id=str(uuid4()),
                request_id=str(uuid4()),
                payload={
                    "session_id": self._session_id,
                    "text": transcript,
                    "user_id": self._user_id,
                    "business_id": self._business_id,
                    "room": self._room,
                    "agent_identity": self._agent_identity,
                },
            )

            self._run_background_task(
                self._send_transcript(
                    webhook_event,
                ),
            )

        self._run_background_task(
            self._update_runtime_state(
                agent_id=self._agent_identity,
                session_status=agent_protocol.JobStatus.JS_RUNNING,
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

            if isinstance(source, tts.TTS):
                logger.warning(
                    "[VoiceSessionHandlers] Recovering from TTS error.",
                )

                error.recoverable = True
                return

            if isinstance(source, stt.STT):
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

            self._run_background_task(
                self._update_runtime_state(
                    session_status=agent_protocol.JobStatus.JS_FAILED,
                    session_error=str(error),
                ),
            )

        @session.on("close")
        def on_close(
            ev: Any,
        ) -> None:

            reason = getattr(ev, "reason", None)
            error = getattr(ev, "error", None)

            reason_value = getattr(
                reason,
                "value",
                str(reason) if reason is not None else "",
            )

            logger.info(
                "[VoiceSessionHandlers] AgentSession closed: "
                "session_id=%s reason=%s error=%s",
                self._session_id,
                reason_value,
                error,
            )

            if reason_value == "error" or error is not None:
                session_error = (
                    str(error)
                    if error is not None
                    else "Agent session closed because of an error."
                )

                self._run_background_task(
                    self._update_runtime_state(
                        session_status=agent_protocol.JobStatus.JS_FAILED,
                        session_error=session_error,
                    ),
                )

                return

            self._run_background_task(
                self._update_runtime_state(
                    session_status=agent_protocol.JobStatus.JS_SUCCESS,
                ),
            )

    async def _update_runtime_state(
        self,
        **updates: Any,
    ) -> None:

        try:
            await voice_agent_service._update_voice_session_state(
                business_id=self._business_id,
                user_id=self._user_id,
                **updates,
            )

        except Exception:

            logger.exception(
                "[VoiceSessionHandlers] "
                "Failed to update voice session state: "
                "session_id=%s updates=%s",
                self._session_id,
                updates,
            )

    async def _send_transcript(
        self,
        event: WebhookEvent,
    ) -> None:

        try:
            await self._webhook_client.send(
                hook=HOOKS.VOICE_AGENT,
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
