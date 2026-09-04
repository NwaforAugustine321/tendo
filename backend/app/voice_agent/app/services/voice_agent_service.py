from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException
from livekit import api
from livekit.protocol import agent as agent_protocol

from app.config.settings import settings
from ..db.mongo_client import get_client

VOICE_SESSIONS_COLLECTION = "voice_sessions"

AGENT_NAME = "tendo-voice"

AGENT_STATE_ATTRIBUTE = "lk.agent.state"

logger = logging.getLogger(__name__)

_livekit: api.LiveKitAPI | None = None


def get_livekit() -> api.LiveKitAPI:
    global _livekit

    try:
        if _livekit is None:
            logger.info(
                "[VoiceService] Creating LiveKit API client: url=%s",
                settings.livekit_url,
            )

            _livekit = api.LiveKitAPI(
                url=settings.livekit_url,
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            )
    except Exception:
        _livekit = None

    return _livekit


class VoiceService:

    def __init__(self) -> None:
        self._livekit: api.LiveKitAPI = get_livekit()

    @staticmethod
    def _status_name(
        status: agent_protocol.JobStatus | int | None,
    ) -> str | None:
        if status is None:
            return None

        if isinstance(status, int):
            try:
                return agent_protocol.JobStatus.Name(status)
            except ValueError:
                return str(status)

        return status.name

    @staticmethod
    def _is_status(
        status: agent_protocol.JobStatus | int | None,
        expected: agent_protocol.JobStatus,
    ) -> bool:
        if status is None:
            return False

        return int(status) == int(expected)

    async def get_voice_session(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        db = get_client()

        return await db[
            VOICE_SESSIONS_COLLECTION
        ].find_one(
            {
                "business_id": business_id,
                "user_id": user_id,
            }
        )

    async def _require_voice_session(
        self,
        *,
        business_id: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        voice_session = await self.get_voice_session(
            business_id=business_id,
            user_id=user_id,
        )

        if voice_session is None:
            raise HTTPException(
                status_code=404,
                detail="Voice session not found.",
            )

        stored_session_id = voice_session.get("session_id")

        if stored_session_id != session_id:
            raise HTTPException(
                status_code=409,
                detail="Voice session does not match the requested session.",
            )

        expected_room = f"tendo-{business_id}"

        if voice_session.get("room") != expected_room:
            raise HTTPException(
                status_code=409,
                detail="Voice session room is invalid.",
            )

        return voice_session

    async def _update_voice_session_state(
        self,
        *,
        business_id: str,
        user_id: str,
        session_status: agent_protocol.JobStatus | int | None = None,
        agent_state: str | None = None,
        agent_id: str | None = None,
        session_error: str | None = None,
    ) -> None:
        db = get_client()

        update: dict[str, Any] = {}

        if session_status is not None:
            update["session_status"] = self._status_name(session_status)

        if agent_state is not None:
            update["agent_state"] = agent_state

        if agent_id is not None:
            update["agent_id"] = agent_id

        if session_error is not None:
            update["session_error"] = session_error

        if len(update) == 1:
            return

        await db[
            VOICE_SESSIONS_COLLECTION
        ].update_one(
            {
                "business_id": business_id,
                "user_id": user_id,
            },
            {
                "$set": update,
            },
        )

    async def _clear_voice_session_state(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> None:
        db = get_client()

        await db[
            VOICE_SESSIONS_COLLECTION
        ].update_one(
            {
                "business_id": business_id,
                "user_id": user_id,
            },
            {
                "$set": {
                    "session_status": None,
                    "agent_state": None,
                    "agent_id": None,
                    "session_error": None,
                },
            },
        )

    async def _list_dispatches(
        self,
        *,
        room: str,
    ) -> list[agent_protocol.AgentDispatch]:
        return await self._livekit.agent_dispatch.list_dispatch(
            room_name=room,
        )

    async def _find_active_dispatches(
        self,
        *,
        room: str,
    ) -> list[agent_protocol.AgentDispatch]:
        dispatches = await self._list_dispatches(
            room=room,
        )

        active: list[agent_protocol.AgentDispatch] = []

        for dispatch in dispatches:
            if dispatch.agent_name != AGENT_NAME:
                continue

            if dispatch.state.deleted_at:
                continue

            for job in dispatch.state.jobs:
                if (
                    self._is_status(
                        job.state.status,
                        agent_protocol.JobStatus.JS_PENDING,
                    )
                    or self._is_status(
                        job.state.status,
                        agent_protocol.JobStatus.JS_RUNNING,
                    )
                ):
                    active.append(dispatch)
                    break

        return active

    async def _find_latest_dispatch(
        self,
        *,
        room: str,
    ) -> agent_protocol.AgentDispatch | None:
        dispatches = await self._list_dispatches(
            room=room,
        )

        matching_dispatches = [
            dispatch
            for dispatch in dispatches
            if (
                dispatch.agent_name == AGENT_NAME
                and not dispatch.state.deleted_at
            )
        ]

        if not matching_dispatches:
            return None

        return max(
            matching_dispatches,
            key=lambda dispatch: dispatch.state.created_at,
        )

    async def _find_dispatch(
        self,
        *,
        room: str,
    ) -> agent_protocol.AgentDispatch | None:
        return await self._find_latest_dispatch(
            room=room,
        )

    async def _delete_active_dispatches(
        self,
        *,
        room: str,
    ) -> None:
        active_dispatches = await self._find_active_dispatches(
            room=room,
        )

        if not active_dispatches:
            return

        for dispatch in active_dispatches:
            logger.warning(
                "[VoiceService] Removing existing active dispatch: "
                "room=%s dispatch_id=%s",
                room,
                dispatch.id,
            )

            try:
                await self._livekit.agent_dispatch.delete_dispatch(
                    dispatch_id=dispatch.id,
                    room_name=room,
                )

                logger.info(
                    "[VoiceService] Existing dispatch removed: "
                    "room=%s dispatch_id=%s",
                    room,
                    dispatch.id,
                )

            except Exception:
                logger.exception(
                    "[VoiceService] Failed to remove existing dispatch: "
                    "room=%s dispatch_id=%s",
                    room,
                    dispatch.id,
                )
                raise

    async def _get_agent_state(
        self,
        *,
        room: str,
        job: agent_protocol.Job,
    ) -> str | None:
        participant_identity = job.state.participant_identity

        if not participant_identity:
            logger.info(
                "[VoiceService] No participant identity yet: "
                "room=%s job=%s",
                room,
                job.id,
            )
            return None

        logger.info(
            "[VoiceService] Looking up agent participant: "
            "room=%s identity=%s",
            room,
            participant_identity,
        )

        try:
            participant = await self._livekit.room.get_participant(
                api.RoomParticipantIdentity(
                    room=room,
                    identity=participant_identity,
                )
            )

        except Exception as exc:
            logger.info(
                "[VoiceService] Agent participant not available yet: "
                "room=%s identity=%s error=%s",
                room,
                participant_identity,
                exc,
            )
            return None

        agent_state = participant.attributes.get(
            AGENT_STATE_ATTRIBUTE,
        )

        logger.info(
            "[VoiceService] Agent participant found: "
            "room=%s identity=%s state=%s",
            room,
            participant_identity,
            agent_state,
        )

        return agent_state

    @classmethod
    def _serialize_job(
        cls,
        job: agent_protocol.Job | None,
    ) -> dict[str, Any] | None:
        if job is None:
            return None

        state = job.state

        return {
            "id": job.id,
            "dispatch_id": job.dispatch_id,
            "status": cls._status_name(
                state.status,
            ),
            "error": state.error or None,
            "started_at": state.started_at or None,
            "ended_at": state.ended_at or None,
            "updated_at": state.updated_at or None,
            "participant_identity": (
                state.participant_identity or None
            ),
            "worker_id": state.worker_id or None,
            "agent_id": state.agent_id or None,
        }

    @staticmethod
    def _serialize_dispatch(
        dispatch: agent_protocol.AgentDispatch | None,
    ) -> dict[str, Any] | None:
        if dispatch is None:
            return None

        return {
            "id": dispatch.id,
            "agent_name": dispatch.agent_name,
            "room": dispatch.room,
            "metadata": dispatch.metadata or None,
            "created_at": dispatch.state.created_at or None,
            "deleted_at": dispatch.state.deleted_at or None,
        }

    @staticmethod
    def _get_latest_job(
        dispatch: agent_protocol.AgentDispatch,
    ) -> agent_protocol.Job | None:
        jobs = list(dispatch.state.jobs)

        if not jobs:
            return None

        return max(
            jobs,
            key=lambda job: job.state.updated_at,
        )

    async def _sync_voice_session(
        self,
        *,
        business_id: str,
        user_id: str,
        room: str,
        dispatch: agent_protocol.AgentDispatch | None,
    ) -> dict[str, Any]:
        if dispatch is None:
            await self._clear_voice_session_state(
                business_id=business_id,
                user_id=user_id,
            )

            return {
                "dispatch": None,
                "job": None,
                "session_status": None,
                "agent_state": None,
                "agent_id": None,
                "session_error": None,
            }

        job = self._get_latest_job(
            dispatch,
        )

        if job is None:
            await self._clear_voice_session_state(
                business_id=business_id,
                user_id=user_id,
            )

            return {
                "dispatch": self._serialize_dispatch(
                    dispatch,
                ),
                "job": None,
                "session_status": None,
                "agent_state": None,
                "agent_id": None,
                "session_error": None,
            }

        session_status = job.state.status

        logger.info(
            "[VoiceService] Syncing dispatch: "
            "room=%s dispatch_id=%s job_id=%s status=%s",
            room,
            dispatch.id,
            job.id,
            self._status_name(session_status),
        )

        agent_state: str | None = None

        if self._is_status(
            session_status,
            agent_protocol.JobStatus.JS_RUNNING,
        ):
            agent_state = await self._get_agent_state(
                room=room,
                job=job,
            )

        agent_id = job.state.agent_id or None

        session_error = job.state.error or None

        logger.info(
            "[VoiceService] Session state: "
            "business_id=%s user_id=%s status=%s "
            "agent_state=%s agent_id=%s error=%s",
            business_id,
            user_id,
            self._status_name(session_status),
            agent_state,
            agent_id,
            session_error,
        )

        await self._update_voice_session_state(
            business_id=business_id,
            user_id=user_id,
            session_status=session_status,
            agent_state=agent_state,
            agent_id=agent_id,
            session_error=session_error,
        )

        return {
            "dispatch": self._serialize_dispatch(
                dispatch,
            ),
            "job": self._serialize_job(
                job,
            ),
            "session_status": self._status_name(
                session_status,
            ),
            "agent_state": agent_state,
            "agent_id": agent_id,
            "session_error": session_error,
        }

    async def start(
        self,
        *,
        business_id: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        voice_session = await self._require_voice_session(
            business_id=business_id,
            user_id=user_id,
            session_id=session_id,
        )

        room = voice_session["room"]

        logger.info(
            "[VoiceService] START requested: "
            "business_id=%s user_id=%s session_id=%s room=%s",
            business_id,
            user_id,
            session_id,
            room,
        )

        await self._delete_active_dispatches(
            room=room,
        )

        await self._clear_voice_session_state(
            business_id=business_id,
            user_id=user_id,
        )

        metadata = json.dumps(
            {
                "business_id": business_id,
                "session_id": session_id,
                "user_id": user_id,
                "room": room,
            },
            separators=(",", ":"),
        )

        dispatch = await self._livekit.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room,
                metadata=metadata,
            )
        )

        logger.info(
            "[VoiceService] Agent dispatch created: "
            "dispatch_id=%s room=%s agent=%s jobs=%s",
            dispatch.id,
            dispatch.room,
            dispatch.agent_name,
            len(dispatch.state.jobs),
        )

        await self._update_voice_session_state(
            business_id=business_id,
            user_id=user_id,
            session_status=(
                self._get_latest_job(dispatch).state.status
                if self._get_latest_job(dispatch) is not None
                else agent_protocol.JobStatus.JS_PENDING
            ),
            agent_state=None,
            agent_id=None,
            session_error=None,
        )

        return {
            "dispatch": self._serialize_dispatch(
                dispatch,
            ),
            "job": self._serialize_job(
                self._get_latest_job(dispatch),
            ),
            "session_status": (
                self._status_name(
                    self._get_latest_job(dispatch).state.status,
                )
                if self._get_latest_job(dispatch) is not None
                else "JS_PENDING"
            ),
            "agent_state": None,
            "agent_id": None,
            "session_error": None,
        }

    async def stop(
        self,
        *,
        business_id: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        voice_session = await self._require_voice_session(
            business_id=business_id,
            user_id=user_id,
            session_id=session_id,
        )

        room = voice_session["room"]

        logger.info(
            "[VoiceService] STOP requested: "
            "business_id=%s user_id=%s session_id=%s room=%s",
            business_id,
            user_id,
            session_id,
            room,
        )

        active_dispatches = await self._find_active_dispatches(
            room=room,
        )

        if not active_dispatches:
            logger.info(
                "[VoiceService] No active dispatch to stop: room=%s",
                room,
            )

            await self._clear_voice_session_state(
                business_id=business_id,
                user_id=user_id,
            )

            return {
                "dispatch": None,
                "job": None,
                "session_status": None,
                "agent_state": None,
                "agent_id": None,
                "session_error": None,
            }

        deleted_dispatch: agent_protocol.AgentDispatch | None = None

        for dispatch in active_dispatches:
            logger.info(
                "[VoiceService] Deleting dispatch: "
                "room=%s dispatch_id=%s",
                room,
                dispatch.id,
            )

            deleted_dispatch = (
                await self._livekit.agent_dispatch.delete_dispatch(
                    dispatch_id=dispatch.id,
                    room_name=room,
                )
            )

        await self._clear_voice_session_state(
            business_id=business_id,
            user_id=user_id,
        )

        return {
            "dispatch": self._serialize_dispatch(
                deleted_dispatch,
            ),
            "job": self._serialize_job(
                self._get_latest_job(deleted_dispatch)
                if deleted_dispatch is not None
                else None,
            ),
            "session_status": None,
            "agent_state": None,
            "agent_id": None,
            "session_error": None,
        }

    async def session_status(
        self,
        *,
        business_id: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        await self._require_voice_session(
            business_id=business_id,
            user_id=user_id,
            session_id=session_id,
        )

        voice_session = await self.get_voice_session(
            business_id=business_id,
            user_id=user_id,
        )

        if voice_session is None:
            raise HTTPException(
                status_code=404,
                detail="Voice session not found.",
            )

        room = voice_session["room"]

        logger.info(
            "[VoiceService] STATUS requested: "
            "business_id=%s user_id=%s session_id=%s room=%s",
            business_id,
            user_id,
            session_id,
            room,
        )

        dispatch = await self._find_dispatch(
            room=room,
        )

        return await self._sync_voice_session(
            business_id=business_id,
            user_id=user_id,
            room=room,
            dispatch=dispatch,
        )


voice_agent_service = VoiceService()
