from __future__ import annotations

import json
import logging
from typing import Any

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
)
from livekit.plugins import langchain

from app.communication.events import ApplicationEvent
from app.communication.interfaces import EventBus

from .events import VoiceSessionRegistry
from .handlers import VoiceSessionHandlers
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
        handlers: VoiceSessionHandlers,
    ) -> None:
        self._event_bus = event_bus
        self._registry = registry
        self._graph = graph
        self._stt = stt
        self._tts = tts
        self._handlers = handlers

    @staticmethod
    def _parse_metadata(
        ctx: JobContext,
    ) -> dict[str, Any]:
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
                "[VoiceSessionService] Invalid JSON metadata: room=%s",
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

    def _get_session_resources(
        self,
        resources: Any,
    ) -> tuple[Any, Any]:
        """
        Get STT/TTS resources for this AgentSession.

        If the resource provider exposes get_stt/get_tts, use those
        so each AgentSession can receive a fresh streaming instance.
        """

        if resources is not None:
            get_stt = getattr(
                resources,
                "get_stt",
                None,
            )

            get_tts = getattr(
                resources,
                "get_tts",
                None,
            )

            if callable(get_stt) and callable(get_tts):
                return (
                    get_stt(),
                    get_tts(),
                )

        return (
            self._stt,
            self._tts,
        )

    async def start(
        self,
        *,
        ctx: JobContext,
        data: VoiceSessionData,
        resources: Any = None,
    ) -> AgentSession:
        """Create, start, register, and announce a voice session."""

        logger.info(
            "[VoiceSessionService] Creating AgentSession: "
            "room=%s session_id=%s user_id=%s",
            ctx.room.name,
            data.session_id,
            data.user_id,
        )

        payload = self._parse_metadata(
            ctx,
        )

        stt = self._stt
        tts = self._tts

        if resources is not None:
            stt, tts = self._get_session_resources(
                resources,
            )

        session = AgentSession(
            stt=stt,
            tts=tts,
            turn_handling=TurnHandlingOptions(
                turn_detection="vad",
                interruption={
                    "mode": "adaptive",
                    "backchannel_boundary": (0.5, 2.0),
                },
                endpointing={
                    "mode": "dynamic",
                },
            ),
        )

        self._handlers.register(
            session,
            resources=resources,
        )

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
                    "payload": payload,
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

        try:
            await session.start(
                agent=agent,
                room=ctx.room,
            )

        except Exception:
            logger.exception(
                "[VoiceSessionService] Failed to start AgentSession: "
                "room=%s session_id=%s",
                ctx.room.name,
                data.session_id,
            )

            try:
                await session.aclose()
            except Exception:
                logger.exception(
                    "[VoiceSessionService] Failed to close "
                    "AgentSession after startup failure.",
                )

            raise

        logger.info(
            "[VoiceSessionService] AgentSession started: "
            "room=%s session_id=%s",
            ctx.room.name,
            data.session_id,
        )

        try:
            await self._registry.register(
                session_id=data.session_id,
                session=session,
            )

        except Exception:
            logger.exception(
                "[VoiceSessionService] Failed to register voice session: "
                "session_id=%s",
                data.session_id,
            )

            await session.aclose()
            raise

        await self._event_bus.publish(
            ApplicationEvent(
                event="voice.agent.ready",
                source="voice-agent",
                correlation_id=data.session_id,
                data={
                    "room": ctx.room.name,
                    "user_id": data.user_id,
                    "business_id": data.business_id,
                    "session_id": data.session_id,
                    "record_id": data.record_id,
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

        try:
            await self._registry.unregister(
                session_id,
            )

        finally:
            await session.aclose()

        logger.info(
            "[VoiceSessionService] Voice session closed: "
            "session_id=%s",
            session_id,
        )
