
from __future__ import annotations

import logging
import os
import sys

from livekit.agents import (
    AgentServer,
    JobContext,
    JobProcess,
)

from ..config import settings
from ..webhooks.client import (
    WebhookClient, WebhookConfig
)
from ..webhooks.contracts import (
    WebhookType,
    HOOKS
)


from .commands import VoiceCommandReceiver
from .metadata import VoiceSessionMetadataParser
from .model import InvalidVoiceSessionMetadata
from .resources import VoiceResources
from .session import VoiceSessionService


os.environ.setdefault(
    "LIVEKIT_URL",
    settings.livekit_url,
)

os.environ.setdefault(
    "LIVEKIT_API_KEY",
    settings.livekit_api_key,
)

os.environ.setdefault(
    "LIVEKIT_API_SECRET",
    settings.livekit_api_secret,
)

os.environ.setdefault(
    "NVIDIA_API_KEY",
    settings.nvidia_api_key,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)


logger = logging.getLogger(
    "voice-worker",
)


logging.getLogger(
    "livekit.agents",
).setLevel(
    logging.WARNING,
)

logging.getLogger(
    "livekit",
).setLevel(
    logging.WARNING,
)

logging.getLogger(
    "asyncio",
).setLevel(
    logging.CRITICAL,
)


sys.path.insert(
    0,
    os.path.dirname(__file__),
)


server = AgentServer(
    num_idle_processes=2,
)


def prewarm(
    proc: JobProcess,
) -> None:

    logger.info(
        "Initializing voice worker process: pid=%s",
        os.getpid(),
    )

    resources = VoiceResources()

    metadata_parser = VoiceSessionMetadataParser()

    proc.userdata["resources"] = resources

    proc.userdata["metadata_parser"] = metadata_parser

    logger.info(
        "Voice worker process initialized: pid=%s",
        os.getpid(),
    )


server.setup_fnc = prewarm


@server.rtc_session(
    agent_name="tendo-voice",
)
async def tendo_session(
    ctx: JobContext,
) -> None:

    resources: VoiceResources = (
        ctx.proc.userdata[
            "resources"
        ]
    )

    metadata_parser: VoiceSessionMetadataParser = (
        ctx.proc.userdata[
            "metadata_parser"
        ]
    )

    metadata = (
        ctx.job.metadata
        or ctx.room.metadata
    )

    try:

        session_data = metadata_parser.parse(
            metadata,
        )

    except InvalidVoiceSessionMetadata as exc:

        logger.error(
            "[tendo_session] Invalid voice session metadata: %s",
            exc,
        )

        await ctx.shutdown()

        return

    logger.info(
        "[tendo_session] Voice session metadata parsed: "
        "room=%s business_id=%s session_id=%s user_id=%s",
        ctx.room.name,
        session_data.business_id,
        session_data.session_id,
        session_data.user_id,
    )

    ctx.log_context_fields = {
        "room": ctx.room.name,
        "session_id": session_data.session_id,
        "user_id": session_data.user_id,
        "business_id": session_data.business_id,
    }

    stt, tts = resources.get()

    webhook_client = WebhookClient(

        hooks={
            HOOKS.VOICE_AGENT: WebhookConfig(
                url=settings.main_server_webhook_url,
                secret=settings.webhook_internal_secret,
                timeout=settings.webhook_default_timeout
            ),
        },
    )

    session_service = VoiceSessionService(
        stt=stt,
        tts=tts,
        webhook_client=webhook_client,
    )

    session = None

    try:

        await webhook_client.start()

        session = await session_service.start(
            ctx=ctx,
            data=session_data,
        )

        command_receiver = VoiceCommandReceiver(
            room=ctx.room,
            user_id=session_data.user_id,
            speak=session.say,
            ctx=ctx
        )

        command_receiver.register()

        logger.info(
            "[tendo_session] Voice session started: "
            "room=%s session_id=%s user_id=%s",
            ctx.room.name,
            session_data.session_id,
            session_data.user_id,
        )

    except Exception:

        logger.exception(
            "[tendo_session] Voice session failed: "
            "room=%s session_id=%s",
            ctx.room.name,
            session_data.session_id,
        )

        if session is not None:

            try:

                await session_service.close(
                    session_id=session_data.session_id,
                    session=session,
                )

            except Exception:

                logger.exception(
                    "[tendo_session] Failed to close failed "
                    "voice session: session_id=%s",
                    session_data.session_id,
                )

        await webhook_client.close()

        raise

    async def _shutdown() -> None:

        logger.info(
            "[tendo_session] Shutting down voice session: "
            "room=%s session_id=%s",
            ctx.room.name,
            session_data.session_id,
        )

        if session is not None:

            try:

                await session_service.close(
                    session_id=session_data.session_id,
                    session=session,
                )

            except Exception:

                logger.exception(
                    "[tendo_session] Failed to close voice session: "
                    "session_id=%s",
                    session_data.session_id,
                )

        await webhook_client.close()

    ctx.add_shutdown_callback(
        _shutdown,
    )
