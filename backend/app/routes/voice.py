import json
import logging
import os

from fastapi import APIRouter, Request, HTTPException

from app.config.settings import settings
from app.services.auth import handle_get_me, COOKIE_NAME
from app.db.tools.sessions import insert_session, find_active_session

router = APIRouter()
logger = logging.getLogger(__name__)

os.environ.setdefault("LIVEKIT_URL", settings.livekit_url)
os.environ.setdefault("LIVEKIT_API_KEY", settings.livekit_api_key)
os.environ.setdefault("LIVEKIT_API_SECRET", settings.livekit_api_secret)

_dispatching_rooms: set[str] = set()


async def _authenticate(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = await handle_get_me(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired.")
    return user


async def _get_voice_context(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")
    business_id = body.get("business_id", "")

    user = await _authenticate(request)
    user_id = user["user_id"]

    if not business_id:
        business_id = user.get("business_id", "")
    if not business_id:
        raise HTTPException(
            status_code=400, detail="No business profile selected.")

    if not session_id:
        existing = await find_active_session(business_id, user_id)
        if existing:
            session_id = existing["id"]
        else:
            new_session = await insert_session(business_id, user_id, title="Voice Session")
            session_id = new_session["id"]

    return user_id, business_id, session_id


@router.post("/voice/token")
async def generate_token(request: Request):
    from livekit.api import AccessToken, VideoGrants, LiveKitAPI
    from livekit.protocol.room import CreateRoomRequest, ListParticipantsRequest
    from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest

    user_id, business_id, session_id = await _get_voice_context(request)

    room_name = f"tendo-{business_id}"
    metadata = json.dumps(
        {"business_id": business_id, "session_id": session_id, "user_id": user_id})

    try:
        async with LiveKitAPI() as api:
            await api.room.create_room(CreateRoomRequest(
                name=room_name,
                metadata=metadata,
                empty_timeout=300,
                departure_timeout=30,
                max_participants=2,
            ))

            should_dispatch = True
            try:
                participants = await api.room.list_participants(ListParticipantsRequest(room=room_name))
                if any(p.identity != user_id for p in participants.participants):
                    should_dispatch = False
            except Exception:
                pass

            if should_dispatch and room_name not in _dispatching_rooms:
                _dispatching_rooms.add(room_name)
                try:
                    await api.agent_dispatch.create_dispatch(CreateAgentDispatchRequest(
                        room=room_name,
                        agent_name="tendo-voice",
                        metadata=metadata,
                    ))
                finally:
                    _dispatching_rooms.discard(room_name)
    except Exception as e:
        logger.warning(f"Room/dispatch: {e}")

    jwt = (
        AccessToken(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        .with_identity(user_id)
        .with_name(user_id)
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_metadata(metadata)
        .to_jwt()
    )

    return {"token": jwt, "url": settings.livekit_url, "room": room_name}


@router.post("/voice/dispatch")
async def dispatch_agent(request: Request):
    from livekit.api import LiveKitAPI
    from livekit.protocol.room import ListParticipantsRequest
    from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest

    body = await request.json()
    room_name = body.get("room", "")
    business_id = body.get("business_id", "")
    session_id = body.get("session_id", "")

    if not room_name:
        raise HTTPException(status_code=400, detail="Room name is required.")

    user = await _authenticate(request)
    user_id = user["user_id"]

    metadata = json.dumps(
        {"business_id": business_id, "session_id": session_id, "user_id": user_id})

    if room_name in _dispatching_rooms:
        return {"status": "already_dispatching"}

    try:
        async with LiveKitAPI() as api:
            try:
                participants = await api.room.list_participants(ListParticipantsRequest(room=room_name))
                if any(p.identity != user_id for p in participants.participants):
                    return {"status": "already_dispatched"}
            except Exception:
                pass

            _dispatching_rooms.add(room_name)
            try:
                await api.agent_dispatch.create_dispatch(CreateAgentDispatchRequest(
                    room=room_name,
                    agent_name="tendo-voice",
                    metadata=metadata,
                ))
            finally:
                _dispatching_rooms.discard(room_name)
    except Exception as e:
        logger.error(f"Agent dispatch failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start voice agent. Please try again.")

    return {"status": "dispatched"}


@router.post("/voice/stop")
async def stop_agent(request: Request):
    from livekit.api import LiveKitAPI
    from livekit.protocol.room import ListParticipantsRequest, RoomParticipantIdentity

    body = await request.json()
    room_name = body.get("room", "")
    if not room_name:
        raise HTTPException(status_code=400, detail="Room name is required.")

    user = await _authenticate(request)

    try:
        async with LiveKitAPI() as api:
            participants = await api.room.list_participants(ListParticipantsRequest(room=room_name))
            for p in participants.participants:
                if p.identity != user["user_id"]:
                    await api.room.remove_participant(RoomParticipantIdentity(
                        room=room_name,
                        identity=p.identity,
                    ))
    except Exception as e:
        logger.warning(f"Stop agent: {e}")

    return {"status": "stopped"}
