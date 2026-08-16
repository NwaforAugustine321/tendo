from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from livekit.api import LiveKitAPI
from livekit.protocol.agent_dispatch import (
    CreateAgentDispatchRequest,
)
from livekit.protocol.room import (
    ListParticipantsRequest,
    RoomParticipantIdentity,
)
from livekit.protocol.agent_dispatch import (
    CreateAgentDispatchRequest,
)
from livekit.protocol.agent import JobStatus
from app.communication.events import ApplicationEvent
from app.config.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOICE_AGENT_NAME = "tendo-voice"

ACTIVE_JOB_STATUSES = frozenset(
    {
        JobStatus.JS_PENDING,
        JobStatus.JS_RUNNING,
    }
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class VoiceLifecycleService:
    """Handles LiveKit voice-agent lifecycle operations."""

    def __init__(self) -> None:
        # Prevent duplicate dispatch requests while a dispatch operation
        # is already running inside this FastAPI process.
        #
        # This is only a local guard. LiveKit dispatch state is checked
        # separately before creating a dispatch.
        self._dispatching_sessions: set[str] = set()

        self._lock = asyncio.Lock()

    # -----------------------------------------------------------------------
    # Event router
    # -----------------------------------------------------------------------

    async def handle(
        self,
        event: ApplicationEvent,
    ) -> None:
        """Handle a voice lifecycle event."""

        if event.event == "voice.session.requested":
            await self.dispatch_agent(
                event,
            )
            return

        if event.event == "voice.session.stop_requested":
            await self.stop_agent(
                event,
            )
            return

        logger.debug(
            "Ignoring unsupported voice lifecycle event: %s",
            event.event,
        )

    # -----------------------------------------------------------------------
    # Dispatch
    # -----------------------------------------------------------------------

    async def dispatch_agent(
        self,
        event: ApplicationEvent,
    ) -> None:
        """
        Dispatch the registered voice agent to a LiveKit room.

        Existing dispatches are inspected before creating a new one.

        A dispatch is reused only when it has an active job:

            JS_PENDING
            JS_RUNNING

        Completed or failed jobs are not considered active and therefore
        allow a new dispatch to be created.
        """

        data = event.data

        if not isinstance(
            data,
            dict,
        ):
            logger.warning(
                "Invalid voice session event data.",
            )
            return

        room_name = str(
            data.get(
                "room",
                "",
            )
        ).strip()

        session_id = str(
            data.get(
                "session_id",
                "",
            )
        ).strip()

        user_id = str(
            data.get(
                "user_id",
                "",
            )
        ).strip()

        business_id = str(
            data.get(
                "business_id",
                "",
            )
        ).strip()

        if not room_name:
            logger.warning(
                "Voice session request has no room.",
            )
            return

        if not session_id:
            logger.warning(
                "Voice session request has no session_id: "
                "room=%s",
                room_name,
            )
            return

        # -------------------------------------------------------------------
        # Local idempotency
        # -------------------------------------------------------------------

        async with self._lock:
            if session_id in self._dispatching_sessions:
                logger.info(
                    "Voice agent dispatch already in progress: "
                    "session_id=%s room=%s",
                    session_id,
                    room_name,
                )
                return

            self._dispatching_sessions.add(
                session_id,
            )

        try:
            metadata = json.dumps(
                {
                    "room": room_name,
                    "user_id": user_id,
                    "business_id": business_id,
                    "session_id": session_id,
                    "record_id": data.get(
                        "record_id",
                        "",
                    ),
                }
            )

            logger.info(
                "Preparing voice agent dispatch: "
                "room=%s session_id=%s user_id=%s",
                room_name,
                session_id,
                user_id,
            )

            async with LiveKitAPI(
                url=settings.livekit_url,
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            ) as api:

                # -----------------------------------------------------------
                # Check existing dispatches
                # -----------------------------------------------------------

                dispatches = (
                    await api.agent_dispatch.list_dispatch(
                        room_name,
                    )
                )

                for existing in dispatches:

                    if (
                        existing.agent_name
                        != VOICE_AGENT_NAME
                    ):
                        continue

                    dispatch_id = getattr(
                        existing,
                        "id",
                        None,
                    )

                    state = getattr(
                        existing,
                        "state",
                        None,
                    )

                    logger.info(
                        "Existing voice dispatch found: "
                        "room=%s dispatch_id=%s",
                        room_name,
                        dispatch_id,
                    )

                    # -------------------------------------------------------
                    # Inspect jobs associated with the dispatch
                    # -------------------------------------------------------

                    jobs = getattr(
                        state,
                        "jobs",
                        [],
                    )

                    if not jobs:
                        logger.info(
                            "Existing dispatch has no jobs yet: "
                            "room=%s dispatch_id=%s",
                            room_name,
                            dispatch_id,
                        )

                        continue

                    active_job_found = False

                    for job in jobs:
                        job_state = getattr(
                            job,
                            "state",
                            None,
                        )

                        status = getattr(
                            job_state,
                            "status",
                            None,
                        )

                        status_name = self._enum_name(
                            status,
                        )

                        logger.info(
                            "Voice dispatch job: "
                            "room=%s "
                            "dispatch_id=%s "
                            "job_id=%s "
                            "status=%s",
                            room_name,
                            dispatch_id,
                            getattr(
                                job,
                                "id",
                                None,
                            ),
                            status_name,
                        )

                        if status_name in ACTIVE_JOB_STATUSES:
                            active_job_found = True

                            logger.info(
                                "Voice agent already active: "
                                "room=%s "
                                "dispatch_id=%s "
                                "job_id=%s "
                                "status=%s",
                                room_name,
                                dispatch_id,
                                getattr(
                                    job,
                                    "id",
                                    None,
                                ),
                                status_name,
                            )

                            break

                    if active_job_found:
                        return

                    # -------------------------------------------------------
                    # Existing dispatch is stale/completed/failed
                    # -------------------------------------------------------

                    logger.info(
                        "Existing voice dispatch is not active: "
                        "room=%s dispatch_id=%s",
                        room_name,
                        dispatch_id,
                    )

                # -----------------------------------------------------------
                # Check connected Agent participants
                # -----------------------------------------------------------

                participants = (
                    await api.room.list_participants(
                        ListParticipantsRequest(
                            room=room_name,
                        ),
                    )
                )

                for participant in participants.participants:

                    if not self._is_agent_participant(
                        participant,
                    ):
                        continue

                    logger.info(
                        "Voice agent already connected: "
                        "room=%s identity=%s",
                        room_name,
                        participant.identity,
                    )

                    return

                # -----------------------------------------------------------
                # Create new LiveKit dispatch
                # -----------------------------------------------------------

                logger.info(
                    "Dispatching voice agent: "
                    "agent=%s room=%s session_id=%s",
                    VOICE_AGENT_NAME,
                    room_name,
                    session_id,
                )

                dispatch = (
                    await api.agent_dispatch.create_dispatch(
                        CreateAgentDispatchRequest(
                            room=room_name,
                            agent_name=VOICE_AGENT_NAME,
                            metadata=metadata,
                        ),
                    )
                )

                dispatch_id = getattr(
                    dispatch,
                    "id",
                    None,
                )

                logger.info(
                    "Voice agent dispatched successfully: "
                    "room=%s session_id=%s dispatch_id=%s",
                    room_name,
                    session_id,
                    dispatch_id,
                )

        except Exception:
            logger.exception(
                "Failed to dispatch voice agent: "
                "room=%s session_id=%s",
                room_name,
                session_id,
            )

            # Allow a later EventBus event to retry.
            raise

        finally:
            async with self._lock:
                self._dispatching_sessions.discard(
                    session_id,
                )

    # -----------------------------------------------------------------------
    # Stop
    # -----------------------------------------------------------------------

    async def stop_agent(
        self,
        event: ApplicationEvent,
    ) -> None:
        """
        Stop the active voice agent.

        The explicit LiveKit dispatch is deleted and any connected
        LiveKit Agent participant is removed.

        The user's participant is never removed.
        """

        data = event.data

        if not isinstance(
            data,
            dict,
        ):
            logger.warning(
                "Invalid voice stop event data.",
            )
            return

        room_name = str(
            data.get(
                "room",
                "",
            )
        ).strip()

        session_id = str(
            data.get(
                "session_id",
                event.correlation_id or "",
            )
        ).strip()

        user_id = str(
            data.get(
                "user_id",
                "",
            )
        ).strip()

        if not room_name:
            logger.warning(
                "Voice stop request has no room: "
                "session_id=%s",
                session_id,
            )
            return

        logger.info(
            "Stopping voice agent: "
            "room=%s session_id=%s user_id=%s",
            room_name,
            session_id,
            user_id,
        )

        try:
            async with LiveKitAPI(
                url=settings.livekit_url,
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            ) as api:

                # -----------------------------------------------------------
                # Delete explicit dispatches
                # -----------------------------------------------------------

                dispatches = (
                    await api.agent_dispatch.list_dispatch(
                        room_name,
                    )
                )

                for dispatch in dispatches:

                    if (
                        dispatch.agent_name
                        != VOICE_AGENT_NAME
                    ):
                        continue

                    dispatch_id = getattr(
                        dispatch,
                        "id",
                        None,
                    )

                    if not dispatch_id:
                        continue

                    try:
                        await api.agent_dispatch.delete_dispatch(
                            dispatch_id,
                            room_name,
                        )

                        logger.info(
                            "Voice agent dispatch deleted: "
                            "room=%s dispatch_id=%s",
                            room_name,
                            dispatch_id,
                        )

                    except Exception:
                        logger.exception(
                            "Failed to delete voice dispatch: "
                            "room=%s dispatch_id=%s",
                            room_name,
                            dispatch_id,
                        )

                # -----------------------------------------------------------
                # Find connected Agent participants
                # -----------------------------------------------------------

                participants = (
                    await api.room.list_participants(
                        ListParticipantsRequest(
                            room=room_name,
                        ),
                    )
                )

                for participant in participants.participants:

                    # Never remove the user's participant.
                    if (
                        user_id
                        and participant.identity
                        == user_id
                    ):
                        continue

                    # Only remove actual LiveKit Agent participants.
                    if not self._is_agent_participant(
                        participant,
                    ):
                        continue

                    try:
                        await api.room.remove_participant(
                            RoomParticipantIdentity(
                                room=room_name,
                                identity=participant.identity,
                            ),
                        )

                        logger.info(
                            "Voice agent participant removed: "
                            "room=%s identity=%s",
                            room_name,
                            participant.identity,
                        )

                    except Exception:
                        logger.exception(
                            "Failed to remove voice agent "
                            "participant: "
                            "room=%s identity=%s",
                            room_name,
                            participant.identity,
                        )

        except Exception:
            logger.exception(
                "Failed to stop voice agent: "
                "room=%s session_id=%s",
                room_name,
                session_id,
            )

            raise

        logger.info(
            "Voice agent stopped: "
            "room=%s session_id=%s",
            room_name,
            session_id,
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _enum_name(
        value: Any,
    ) -> str:
        """
        Return a stable enum name for protobuf enum values.

        Handles both generated enum values and string-like values.
        """

        if value is None:
            return ""

        name = getattr(
            value,
            "name",
            None,
        )

        if name:
            return str(
                name,
            ).upper()

        value_string = str(
            value,
        ).upper()

        # Protobuf string representations can sometimes look like:
        #
        #     JS_RUNNING
        #
        # or:
        #
        #     JobStatus.JS_RUNNING
        #
        if "." in value_string:
            value_string = value_string.rsplit(
                ".",
                1,
            )[-1]

        return value_string

    @staticmethod
    def _is_agent_participant(
        participant: Any,
    ) -> bool:
        """
        Return True when a LiveKit participant is an Agent.

        LiveKit exposes the participant kind through ParticipantInfo.Kind.
        The current protocol value for AGENT is 4.
        """

        kind = getattr(
            participant,
            "kind",
            None,
        )

        if kind is None:
            return False

        # Prefer enum name when available.
        kind_name = getattr(
            kind,
            "name",
            None,
        )

        if kind_name:
            return str(
                kind_name,
            ).upper().endswith(
                "AGENT",
            )

        try:
            return int(
                kind,
            ) == 4

        except (
            TypeError,
            ValueError,
        ):
            return False


# ---------------------------------------------------------------------------
# Shared service
# ---------------------------------------------------------------------------

voice_lifecycle_service = VoiceLifecycleService()
