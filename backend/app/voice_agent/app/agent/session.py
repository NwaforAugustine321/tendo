from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    ModelSettings,
    TurnHandlingOptions,
)

from ..webhooks.client import WebhookClientInterface
from .handlers import VoiceSessionHandlers
from .model import VoiceSessionData

logger = logging.getLogger(__name__)

_TTS_MAX_CHARS = 250


class VoiceAgent(Agent):

    @staticmethod
    def _split_text(
        text: str,
        *,
        max_chars: int = _TTS_MAX_CHARS,
    ) -> list[str]:

        if not text:
            return []

        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        remaining = text

        while len(remaining) > max_chars:

            candidate = remaining[:max_chars]

            sentence_matches = list(
                re.finditer(
                    r"[.!?](?:[\"\'”’)\]]*)?(?:\s+|$)",
                    candidate,
                )
            )

            if sentence_matches:
                boundary = sentence_matches[-1].end()

                if boundary > 0:
                    chunks.append(
                        remaining[:boundary],
                    )

                    remaining = remaining[boundary:]

                    continue

            whitespace_boundary = max(
                candidate.rfind(" "),
                candidate.rfind("\n"),
                candidate.rfind("\t"),
            )

            if whitespace_boundary > 0:
                chunks.append(
                    remaining[:whitespace_boundary],
                )

                remaining = remaining[whitespace_boundary:]

                continue

            chunks.append(
                remaining[:max_chars],
            )

            remaining = remaining[max_chars:]

        if remaining:
            chunks.append(
                remaining,
            )

        return chunks

    @classmethod
    async def _chunk_text(
        cls,
        text: AsyncIterable[str],
    ) -> AsyncIterator[str]:

        buffer = ""

        async for delta in text:

            if not delta:
                continue

            buffer += delta

            while len(buffer) > _TTS_MAX_CHARS:

                chunks = cls._split_text(
                    buffer,
                    max_chars=_TTS_MAX_CHARS,
                )

                if not chunks:
                    break

                if len(chunks) == 1:

                    chunk = chunks[0]

                    if (
                        not chunk
                        or len(chunk) >= len(buffer)
                    ):
                        break

                    buffer = buffer[len(chunk):]

                    yield chunk

                    continue

                for chunk in chunks[:-1]:

                    if chunk:
                        yield chunk

                buffer = chunks[-1]

        if buffer:
            yield buffer

    async def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings: ModelSettings,
    ) -> AsyncIterator[rtc.AudioFrame]:

        logger.debug(
            "[VoiceAgent] Starting NVIDIA TTS text chunking: "
            "max_chars=%s",
            _TTS_MAX_CHARS,
        )

        chunked_text = self._chunk_text(
            text,
        )

        async for frame in Agent.default.tts_node(
            self,
            chunked_text,
            model_settings,
        ):
            yield frame


class VoiceSessionService:

    def __init__(
        self,
        *,
        stt: Any,
        tts: Any,
        webhook_client: WebhookClientInterface,
    ) -> None:

        self._stt = stt
        self._tts = tts
        self._webhook_client = webhook_client

    async def start(
        self,
        *,
        ctx: JobContext,
        data: VoiceSessionData,
    ) -> AgentSession:

        logger.info(
            "[VoiceSessionService] Job entered: "
            "room=%s session_id=%s user_id=%s "
            "job_id=%s worker_id=%s",
            ctx.room.name,
            data.session_id,
            data.user_id,
            ctx.job.id,
            ctx.worker_id,
        )

        logger.info(
            "[VoiceSessionService] Creating AgentSession: "
            "room=%s session_id=%s user_id=%s",
            ctx.room.name,
            data.session_id,
            data.user_id,
        )

        session = AgentSession(
            stt=self._stt,
            tts=self._tts,
            turn_handling=TurnHandlingOptions(
                turn_detection="vad",
                interruption={
                    "mode": "adaptive",
                    "backchannel_boundary": (
                        0.5,
                        2.0,
                    ),
                },
                endpointing={
                    "mode": "dynamic",
                },
            ),
        )

        logger.info(
            "[VoiceSessionService] AgentSession created: "
            "room=%s session_id=%s",
            ctx.room.name,
            data.session_id,
        )

        handlers = VoiceSessionHandlers(
            webhook_client=self._webhook_client,
            session_id=data.session_id,
            user_id=data.user_id,
            business_id=data.business_id,
            oom_name=data.room_name
        )

        handlers.register(session)

        logger.info(
            "[VoiceSessionService] Session handlers registered: "
            "room=%s session_id=%s",
            ctx.room.name,
            data.session_id,
        )

        agent = VoiceAgent(
            instructions=(
                "You are Tendo, a helpful voice AI assistant. "
                "Speak naturally, clearly, and concisely. "
                "Keep responses conversational and appropriate "
                "for voice."
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
                "[VoiceSessionService] AgentSession.start failed: "
                "room=%s session_id=%s",
                ctx.room.name,
                data.session_id,
            )

            try:

                await session.aclose()

            except Exception:

                logger.exception(
                    "[VoiceSessionService] Failed to close "
                    "AgentSession after startup failure: "
                    "session_id=%s",
                    data.session_id,
                )

            raise

        logger.info(
            "[VoiceSessionService] AgentSession.start completed: "
            "room=%s session_id=%s",
            ctx.room.name,
            data.session_id,
        )

        try:

            local_participant = (
                ctx.room.local_participant
            )

            logger.info(
                "[VoiceSessionService] Local agent participant: "
                "room=%s identity=%s sid=%s",
                ctx.room.name,
                local_participant.identity,
                local_participant.sid,
            )

        except Exception:

            logger.exception(
                "[VoiceSessionService] Failed to inspect "
                "local participant after AgentSession.start: "
                "room=%s session_id=%s",
                ctx.room.name,
                data.session_id,
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

        logger.info(
            "[VoiceSessionService] Closing voice session: "
            "session_id=%s",
            session_id,
        )

        try:

            await session.aclose()

        except Exception:

            logger.exception(
                "[VoiceSessionService] Failed to close AgentSession: "
                "session_id=%s",
                session_id,
            )

            raise

        finally:

            logger.info(
                "[VoiceSessionService] Voice session closed: "
                "session_id=%s",
                session_id,
            )
