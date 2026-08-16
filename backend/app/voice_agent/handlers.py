from __future__ import annotations

import logging

from livekit.agents import AgentSession, ErrorEvent, llm, stt, tts

logger = logging.getLogger(__name__)


class VoiceSessionHandlers:
    """Registers lifecycle handlers for a voice session."""

    def register(
        self,
        session: AgentSession,
    ) -> None:

        @session.on("error")
        def on_error(
            ev: ErrorEvent,
        ) -> None:

            if ev.error.recoverable:
                return

            if isinstance(
                ev.source,
                (tts.TTS, llm.LLM),
            ):
                ev.error.recoverable = True
                return

            if isinstance(
                ev.source,
                stt.STT,
            ):
                session.update_agent(
                    session.current_agent,
                )
                ev.error.recoverable = True
                return

        @session.on("close")
        def on_close(
            *args,
        ) -> None:
            logger.info(
                "[tendo_session] Session closed",
            )
