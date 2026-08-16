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

from app.communication.events import ApplicationEvent
from app.config.settings import settings

logger = logging.getLogger(__name__)


VOICE_AGENT_NAME = "tendo-voice"

ACTIVE_JOB_STATUSES = frozenset(
    {
        "JS_PENDING",
        "JS_RUNNING",
    },
)


class VoiceLifecycleService:
    """Handles LiveKit voice-agent lifecycle operations."""

    def __init__(self) -> None:
        # Prevent duplicate dispatch requests for the same user
        # while a dispatch operation is already running.
        self._dispatching_users: set[str] = set()

        self._lock = asyncio.Lock()

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

    async def dispatch_agent(
        self,
        event: ApplicationEvent,
    ) -> None:
        """
        Ensure that the user's voice agent is running.

        The dispatch/job state is the source of truth.

        A stale participant in the room does not block a new dispatch.
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

        room_name = self._string(
            data.get("room"),
        )

        user_id = self._string(
            data.get("user_id"),
        )

        if not room_name:
            logger.warning(
                "Voice session request has no room.",
            )
            return

        if not user_id:
            logger.warning(
                "Voice session request has no user_id: room=%s",
                room_name,
            )
            return

        agent_identity = self.agent_identity(
            user_id,
        )

        async with self._lock:
            if user_id in self._dispatching_users:
                logger.info(
                    "Voice agent dispatch already in progress: "
                    "room=%s user_id=%s",
                    room_name,
                    user_id,
                )
                return

            self._dispatching_users.add(
                user_id,
            )

        try:
            metadata = json.dumps(
                {
                    **data,
                    "room": room_name,
                    "user_id": user_id,
                    "agent_identity": agent_identity,
                },
            )

            logger.info(
                "Preparing voice agent dispatch: "
                "agent=%s identity=%s room=%s user_id=%s ",
                VOICE_AGENT_NAME,
                agent_identity,
                room_name,
                user_id,

            )

            async with LiveKitAPI(
                url=settings.livekit_url,
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            ) as api:

                dispatches = (
                    await api.agent_dispatch.list_dispatch(
                        room_name,
                    )
                )

                active_dispatch_found = False

                for dispatch in dispatches:
                    if (
                        getattr(
                            dispatch,
                            "agent_name",
                            "",
                        )
                        != VOICE_AGENT_NAME
                    ):
                        continue

                    dispatch_user_id = (
                        self._get_dispatch_user_id(
                            dispatch,
                        )
                    )

                    if dispatch_user_id != user_id:
                        continue

                    dispatch_id = getattr(
                        dispatch,
                        "id",
                        None,
                    )

                    state = getattr(
                        dispatch,
                        "state",
                        None,
                    )

                    jobs = getattr(
                        state,
                        "jobs",
                        [],
                    )

                    logger.info(
                        "Existing voice dispatch found: "
                        "room=%s user_id=%s dispatch_id=%s",
                        room_name,
                        user_id,
                        dispatch_id,
                    )

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
                            "room=%s user_id=%s dispatch_id=%s "
                            "job_id=%s status=%s",
                            room_name,
                            user_id,
                            dispatch_id,
                            getattr(
                                job,
                                "id",
                                None,
                            ),
                            status_name,
                        )

                        if status_name in ACTIVE_JOB_STATUSES:
                            active_dispatch_found = True

                            logger.info(
                                "Voice agent is already active: "
                                "room=%s user_id=%s "
                                "dispatch_id=%s job_id=%s status=%s",
                                room_name,
                                user_id,
                                dispatch_id,
                                getattr(
                                    job,
                                    "id",
                                    None,
                                ),
                                status_name,
                            )

                            break

                    if active_dispatch_found:
                        break

                    if dispatch_id:
                        try:
                            await api.agent_dispatch.delete_dispatch(
                                dispatch_id,
                                room_name,
                            )

                            logger.info(
                                "Removed stale voice dispatch: "
                                "room=%s user_id=%s dispatch_id=%s",
                                room_name,
                                user_id,
                                dispatch_id,
                            )

                        except Exception:
                            logger.exception(
                                "Failed to remove stale voice dispatch: "
                                "room=%s user_id=%s dispatch_id=%s",
                                room_name,
                                user_id,
                                dispatch_id,
                            )

                if active_dispatch_found:
                    return

                participants = (
                    await api.room.list_participants(
                        ListParticipantsRequest(
                            room=room_name,
                        ),
                    )
                )

                stale_agent_found = False

                for participant in (
                    participants.participants
                ):
                    identity = self._string(
                        participant.identity,
                    )

                    if identity != agent_identity:
                        continue

                    stale_agent_found = True

                    logger.warning(
                        "Found stale voice agent participant: "
                        "room=%s user_id=%s identity=%s",
                        room_name,
                        user_id,
                        identity,
                    )

                    # -------------------------------------------------------
                    # IMPORTANT:
                    #
                    # We only remove the exact agent identity.
                    # The user's participant is untouched.
                    # -------------------------------------------------------

                    try:
                        await api.room.remove_participant(
                            RoomParticipantIdentity(
                                room=room_name,
                                identity=identity,
                            ),
                        )

                        logger.info(
                            "Removed stale voice agent participant: "
                            "room=%s user_id=%s identity=%s",
                            room_name,
                            user_id,
                            identity,
                        )

                    except Exception:
                        logger.exception(
                            "Failed to remove stale voice agent participant: "
                            "room=%s user_id=%s identity=%s",
                            room_name,
                            user_id,
                            identity,
                        )

                # -----------------------------------------------------------
                # 3. Dispatch fresh agent
                # -----------------------------------------------------------

                logger.info(
                    "Dispatching fresh voice agent: "
                    "agent=%s identity=%s room=%s "
                    "user_id=%s",
                    VOICE_AGENT_NAME,
                    agent_identity,
                    room_name,
                    user_id,

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
                    "room=%s user_id=%s identity=%s "
                    " dispatch_id=%s",
                    room_name,
                    user_id,
                    agent_identity,

                    dispatch_id,
                )

        except Exception:
            logger.exception(
                "Failed to dispatch voice agent: "
                "room=%s user_id=%s",
                room_name,
                user_id,

            )

            raise

        finally:
            async with self._lock:
                self._dispatching_users.discard(
                    user_id,
                )

    async def stop_agent(
        self,
        event: ApplicationEvent,
    ) -> None:
        """
        Stop the voice agent belonging to the user.

        Only the user's agent identity is removed.
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

        room_name = self._string(
            data.get("room"),
        )

        user_id = self._string(
            data.get("user_id"),
        )

        if not room_name:
            logger.warning(
                "Voice stop request has no room.",
            )
            return

        if not user_id:
            logger.warning(
                "Voice stop request has no user_id.",
            )
            return

        agent_identity = self.agent_identity(
            user_id,
        )

        logger.info(
            "Stopping voice agent: "
            "room=%s user_id=%s identity=%s",
            room_name,
            user_id,
            agent_identity,

        )

        try:
            async with LiveKitAPI(
                url=settings.livekit_url,
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            ) as api:

                # -----------------------------------------------------------
                # Delete user's dispatches
                # -----------------------------------------------------------

                dispatches = (
                    await api.agent_dispatch.list_dispatch(
                        room_name,
                    )
                )

                for dispatch in dispatches:
                    if (
                        getattr(
                            dispatch,
                            "agent_name",
                            "",
                        )
                        != VOICE_AGENT_NAME
                    ):
                        continue

                    dispatch_user_id = (
                        self._get_dispatch_user_id(
                            dispatch,
                        )
                    )

                    if dispatch_user_id != user_id:
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
                            "room=%s user_id=%s dispatch_id=%s",
                            room_name,
                            user_id,
                            dispatch_id,
                        )

                    except Exception:
                        logger.exception(
                            "Failed to delete voice dispatch: "
                            "room=%s user_id=%s dispatch_id=%s",
                            room_name,
                            user_id,
                            dispatch_id,
                        )

                # -----------------------------------------------------------
                # Remove only this user's agent participant
                # -----------------------------------------------------------

                participants = (
                    await api.room.list_participants(
                        ListParticipantsRequest(
                            room=room_name,
                        ),
                    )
                )

                for participant in (
                    participants.participants
                ):
                    identity = self._string(
                        participant.identity,
                    )

                    if identity != agent_identity:
                        continue

                    try:
                        await api.room.remove_participant(
                            RoomParticipantIdentity(
                                room=room_name,
                                identity=identity,
                            ),
                        )

                        logger.info(
                            "Voice agent participant removed: "
                            "room=%s user_id=%s identity=%s",
                            room_name,
                            user_id,
                            identity,
                        )

                    except Exception:
                        logger.exception(
                            "Failed to remove voice agent participant: "
                            "room=%s user_id=%s identity=%s",
                            room_name,
                            user_id,
                            identity,
                        )

        except Exception:
            logger.exception(
                "Failed to stop voice agent: "
                "room=%s user_id=%s ",
                room_name,
                user_id,

            )

            raise

        logger.info(
            "Voice agent stopped: "
            "room=%s user_id=%s identity=%s",
            room_name,
            user_id,
            agent_identity,

        )

    @staticmethod
    def agent_identity(
        user_id: str,
    ) -> str:
        """Return the LiveKit identity belonging to a user."""

        return f"voice-agent-{user_id}"

    @staticmethod
    def _get_dispatch_user_id(
        dispatch: Any,
    ) -> str:
        """Extract user_id from dispatch metadata."""

        metadata = getattr(
            dispatch,
            "metadata",
            "",
        )

        if not metadata:
            return ""

        try:
            payload = json.loads(
                metadata,
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            return ""

        if not isinstance(
            payload,
            dict,
        ):
            return ""

        return VoiceLifecycleService._string(
            payload.get("user_id"),
        )

    @staticmethod
    def _enum_name(
        value: Any,
    ) -> str:
        """Return a stable enum name."""

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

        if "." in value_string:
            value_string = value_string.rsplit(
                ".",
                1,
            )[-1]

        return value_string

    @staticmethod
    def _string(
        value: Any,
    ) -> str:
        """Normalize a value to a trimmed string."""

        if value is None:
            return ""

        return str(
            value,
        ).strip()


voice_lifecycle_service = VoiceLifecycleService()
