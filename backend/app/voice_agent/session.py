from __future__ import annotations

import json
import logging
from typing import Any

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    inference,
)
from livekit.plugins import langchain

from app.communication.events import ApplicationEvent
from app.communication.interfaces import EventBus

from .events import VoiceSessionRegistry
from .model import VoiceSessionData

logger = logging.getLogger(__name__)


class VoiceSessionService:
    """Creates and manages a LiveKit voice session."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        registry: VoiceSessionRegistry,
        graph: Any,
        stt: Any,
        tts: Any,
    ) -> None:
        self._event_bus = event_bus
        self._registry = registry
        self._graph = graph
        self._stt = stt
        self._tts = tts

    @staticmethod
    def _parse_metadata(
        ctx: JobContext,
    ) -> dict[str, Any]:
        """
        Parse the original LiveKit job/room metadata.

        The voice agent does not make assumptions about the fields
        contained in the metadata. The application decides what
        context to provide when dispatching the agent.
        """

        raw_metadata = (
            ctx.job.metadata
            or ctx.room.metadata
            or ""
        )

        if not raw_metadata:
            return {}

        try:
            payload = json.loads(
                raw_metadata,
            )

        except json.JSONDecodeError:
            logger.warning(
                "[VoiceSessionService] Invalid JSON metadata: "
                "room=%s",
                ctx.room.name,
            )
            return {}

        if not isinstance(
            payload,
            dict,
        ):
            logger.warning(
                "[VoiceSessionService] Voice metadata must be "
                "a JSON object: room=%s",
                ctx.room.name,
            )
            return {}

        return payload

    async def start(
        self,
        *,
        ctx: JobContext,
        data: VoiceSessionData,
    ) -> AgentSession:
        """
        Create, start, register, and announce a voice session.

        Application-specific context is obtained from the LiveKit
        metadata and passed to the graph without the voice-agent
        service knowing which fields the application provides.
        """

        logger.info(
            "[VoiceSessionService] Creating AgentSession: "
            "room=%s session_id=%s",
            ctx.room.name,
            data.session_id,
        )

        payload = self._parse_metadata(
            ctx,
        )

        logger.debug(
            "[VoiceSessionService] Voice payload loaded: "
            "room=%s keys=%s",
            ctx.room.name,
            list(payload.keys()),
        )

        session = AgentSession(
            stt=self._stt,
            tts=self._tts,
            turn_handling=TurnHandlingOptions(
                turn_detection=inference.TurnDetector(),
                interruption={
                    "mode": "adaptive",
                    "backchannel_boundary": (0.5, 2.0),
                },
                endpointing={
                    "mode": "dynamic",
                },
            ),
        )

        # ------------------------------------------------------------------
        # Graph / LLM
        # ------------------------------------------------------------------

        agent = Agent(
            instructions=(
                "You are Tendo, a helpful voice AI assistant. "
                "Listen carefully to the user and respond naturally "
                "and concisely."
            ),
            llm=langchain.LLMAdapter(
                graph=self._graph,
                stream_mode="custom",
                context={
                    "session": session,
                    "payload":  payload,
                },
                config={
                    "configurable": {
                        "thread_id": data.session_id,
                    },
                },
            ),
        )

        logger.info(
            "[VoiceSessionService] Starting AgentSession: "
            "room=%s session_id=%s",
            ctx.room.name,
            data.session_id,
        )

        await session.start(
            agent=agent,
            room=ctx.room,
        )

        logger.info(
            "[VoiceSessionService] AgentSession started: "
            "room=%s session_id=%s",
            ctx.room.name,
            data.session_id,
        )

        # ------------------------------------------------------------------
        # Register runtime session
        # ------------------------------------------------------------------

        await self._registry.register(
            session_id=data.session_id,
            session=session,
        )

        logger.info(
            "[VoiceSessionService] Voice session registered: "
            "session_id=%s",
            data.session_id,
        )

        # ------------------------------------------------------------------
        # Announce readiness
        # ------------------------------------------------------------------

        await self._event_bus.publish(
            ApplicationEvent(
                event="voice.agent.ready",
                source="voice-agent",
                correlation_id=data.session_id,
                data={
                    "room": ctx.room.name,
                },
            ),
        )

        logger.info(
            "[VoiceSessionService] Voice agent ready: "
            "room=%s session_id=%s user_id=%s",
            ctx.room.name,
            data.session_id,
            data.user_id,
        )

        return session

    async def close(
        self,
        *,
        session_id: str,
        session: AgentSession,
    ) -> None:
        """Unregister and close a voice session."""

        logger.info(
            "[VoiceSessionService] Closing voice session: "
            "session_id=%s",
            session_id,
        )

        await self._registry.unregister(
            session_id,
        )

        await session.aclose()

        logger.info(
            "[VoiceSessionService] Voice session closed: "
            "session_id=%s",
            session_id,
        )
