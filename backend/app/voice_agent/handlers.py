from __future__ import annotations

import logging
from typing import Any

from livekit.agents import (
    AgentSession,
    ErrorEvent,
    llm,
    stt,
    tts,
)

logger = logging.getLogger(__name__)


class VoiceSessionHandlers:
    """Registers lifecycle and recovery handlers for a voice session."""

    def register(
        self,
        session: AgentSession,
        resources: Any = None,
    ) -> None:
        """Register AgentSession lifecycle handlers.

        Args:
            session: The AgentSession to register handlers on.
            resources: VoiceResources instance used to create fresh
                STT instances on error recovery.
        """

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

            # ---------------------------------------------------------------
            # LLM
            # ---------------------------------------------------------------

            if isinstance(
                source,
                llm.LLM,
            ):
                logger.warning(
                    "[VoiceSessionHandlers] Recovering from LLM error.",
                )

                error.recoverable = True
                return

            # ---------------------------------------------------------------
            # TTS
            # ---------------------------------------------------------------

            if isinstance(
                source,
                tts.TTS,
            ):
                logger.warning(
                    "[VoiceSessionHandlers] Recovering from TTS error.",
                )

                error.recoverable = True
                return

            # ---------------------------------------------------------------
            # STT
            # ---------------------------------------------------------------

            if isinstance(
                source,
                stt.STT,
            ):
                logger.warning(
                    "[VoiceSessionHandlers] "
                    "STT error detected. Creating fresh STT instance.",
                )

                try:
                    # Create a completely fresh STT instance to avoid
                    # stale gRPC sequence state. The Riva streaming API
                    # requires a START flag on the first request of each
                    # sequence — reusing a corrupted connection causes
                    # INVALID_ARGUMENT errors.
                    if resources is not None:
                        fresh_stt = resources.create_stt()
                        session._stt = fresh_stt

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

            # ---------------------------------------------------------------
            # Unknown error
            # ---------------------------------------------------------------

            logger.error(
                "[VoiceSessionHandlers] "
                "Unhandled unrecoverable error: "
                "source=%s error=%s",
                type(source).__name__,
                error,
            )

        # -------------------------------------------------------------------
        # Session close
        # -------------------------------------------------------------------

        @session.on("close")
        def on_close(
            *args,
        ) -> None:
            logger.info(
                "[VoiceSessionHandlers] AgentSession closed.",
            )
