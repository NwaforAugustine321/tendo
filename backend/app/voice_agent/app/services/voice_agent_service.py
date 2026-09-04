from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from livekit import api
from livekit.protocol import agent as agent_protocol

from app.config.settings import settings
from ..db.mongo_client import get_client


VOICE_SESSIONS_COLLECTION = "voice_sessions"

AGENT_NAME = "tendo-voice"

AGENT_STATE_ATTRIBUTE = "lk.agent.state"


_livekit: api.LiveKitAPI | None = None


def get_livekit() -> api.LiveKitAPI:
    global _livekit

    if _livekit is None:
        _livekit = api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )

    return _livekit


class VoiceService:

    def __init__(self) -> None:
        self._livekit: api.LiveKitAPI = get_livekit()

    # ================================================================
    # MONGODB
    # ================================================================

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
        session_status: agent_protocol.JobStatus | None,
        agent_state: str | None,
        agent_id: str | None,
        session_error: str | None,
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
                    "session_status": (
                        session_status.name
                        if session_status is not None
                        else None
                    ),
                    "agent_state": agent_state,
                    "agent_id": agent_id,
                    "session_error": session_error,
                },
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

    # ================================================================
    # LIVEKIT DISPATCH
    # ================================================================

    async def _list_dispatches(
        self,
        *,
        room: str,
    ) -> list[agent_protocol.AgentDispatch]:
        response = await self._livekit.agent_dispatch.list_dispatch(
            api.ListAgentDispatchRequest(
                room=room,
            )
        )

        return list(response.agent_dispatches)

    async def _find_active_dispatch(
        self,
        *,
        room: str,
    ) -> agent_protocol.AgentDispatch | None:
        dispatches = await self._list_dispatches(
            room=room,
        )

        for dispatch in dispatches:
            if dispatch.agent_name != AGENT_NAME:
                continue

            for job in dispatch.state.jobs:
                if job.state.status in (
                    agent_protocol.JobStatus.JS_PENDING,
                    agent_protocol.JobStatus.JS_RUNNING,
                ):
                    return dispatch

        return None

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
            if dispatch.agent_name == AGENT_NAME
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
        """
        Return the active dispatch when one exists.

        If there is no active dispatch, return the latest dispatch.
        This prevents an older completed dispatch from being selected
        when a newer active dispatch exists.
        """

        active_dispatch = await self._find_active_dispatch(
            room=room,
        )

        if active_dispatch is not None:
            return active_dispatch

        return await self._find_latest_dispatch(
            room=room,
        )

    # ================================================================
    # LIVEKIT JOB
    # ================================================================

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

    # ================================================================
    # LIVEKIT AGENT STATE
    # ================================================================

    async def _get_agent_state(
        self,
        *,
        room: str,
        job: agent_protocol.Job,
    ) -> str | None:
        """
        AgentSession state is published by the LiveKit agent
        participant through the `lk.agent.state` attribute.

        The value is not part of JobState.
        """

        participant_identity = job.state.participant_identity

        if not participant_identity:
            return None

        try:
            participant = await self._livekit.room.get_participant(
                api.RoomParticipantIdentity(
                    room=room,
                    identity=participant_identity,
                )
            )
        except Exception:
            return None

        return participant.attributes.get(
            AGENT_STATE_ATTRIBUTE,
        )

    # ================================================================
    # JSON SERIALIZATION
    # ================================================================

    @staticmethod
    def _serialize_job(
        job: agent_protocol.Job | None,
    ) -> dict[str, Any] | None:
        if job is None:
            return None

        state = job.state

        return {
            "id": job.id,
            "dispatch_id": job.dispatch_id,
            "status": (
                state.status.name
                if state.status is not None
                else None
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

    # ================================================================
    # SYNCHRONIZE SESSION STATE
    # ================================================================

    async def _sync_voice_session(
        self,
        *,
        business_id: str,
        user_id: str,
        room: str,
        dispatch: agent_protocol.AgentDispatch | None,
    ) -> dict[str, Any]:
        """
        Synchronize MongoDB with the current LiveKit session state.

        LiveKit remains the source of truth.

        MongoDB stores only the latest application-facing snapshot.
        """

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
                "dispatch": self._serialize_dispatch(dispatch),
                "job": None,
                "session_status": None,
                "agent_state": None,
                "agent_id": None,
                "session_error": None,
            }

        session_status = job.state.status

        agent_state: str | None = None

        if session_status == agent_protocol.JobStatus.JS_RUNNING:
            agent_state = await self._get_agent_state(
                room=room,
                job=job,
            )

        agent_id = job.state.agent_id or None

        session_error = job.state.error or None

        await self._update_voice_session_state(
            business_id=business_id,
            user_id=user_id,
            session_status=session_status,
            agent_state=agent_state,
            agent_id=agent_id,
            session_error=session_error,
        )

        return {
            "dispatch": self._serialize_dispatch(dispatch),
            "job": self._serialize_job(job),
            "session_status": (
                session_status.name
                if session_status is not None
                else None
            ),
            "agent_state": agent_state,
            "agent_id": agent_id,
            "session_error": session_error,
        }

    # ================================================================
    # START
    # ================================================================

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

        active_dispatch = await self._find_active_dispatch(
            room=room,
        )

        if active_dispatch is not None:
            return await self._sync_voice_session(
                business_id=business_id,
                user_id=user_id,
                room=room,
                dispatch=active_dispatch,
            )

        metadata = json.dumps(
            {
                "business_id": business_id,
                "session_id": session_id,
                "user_id": user_id,
                "room": room,
            },
            separators=(
                ",",
                ":",
            ),
        )

        dispatch = await self._livekit.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room,
                metadata=metadata,
            )
        )

        return await self._sync_voice_session(
            business_id=business_id,
            user_id=user_id,
            room=room,
            dispatch=dispatch,
        )

    # ================================================================
    # STOP
    # ================================================================

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

        active_dispatch = await self._find_active_dispatch(
            room=room,
        )

        if active_dispatch is None:
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

        deleted_dispatch = (
            await self._livekit.agent_dispatch.delete_dispatch(
                api.DeleteAgentDispatchRequest(
                    dispatch_id=active_dispatch.id,
                    room=room,
                )
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
                self._get_latest_job(
                    deleted_dispatch,
                )
            ),
            "session_status": None,
            "agent_state": None,
            "agent_id": None,
            "session_error": None,
        }

    # ================================================================
    # SESSION STATUS
    # ================================================================

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
