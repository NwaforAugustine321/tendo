"""Voice routes — LiveKit token generation with agent dispatch."""

import json
import logging
import time

from fastapi import APIRouter, Request

from app.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/voice/token")
async def generate_token(request: Request):
    """Generate a LiveKit access token and dispatch agent to the room."""
    import os
    from livekit.api import AccessToken, VideoGrants, LiveKitAPI
    from livekit.protocol.room import CreateRoomRequest
    from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest
    from app.services.auth import handle_get_me, COOKIE_NAME

    os.environ.setdefault("LIVEKIT_URL", settings.livekit_url)
    os.environ.setdefault("LIVEKIT_API_KEY", settings.livekit_api_key)
    os.environ.setdefault("LIVEKIT_API_SECRET", settings.livekit_api_secret)

    body = await request.json()
    session_id = body.get("session_id", "")
    business_id = body.get("business_id", "")
    user_id = ""

    # Get authenticated user from cookie
    from app.services.auth import handle_get_me, COOKIE_NAME
    token = request.cookies.get(COOKIE_NAME)
    if token:
        user = await handle_get_me(token)
        if user:
            user_id = user.get("user_id", "")
            if not business_id and user.get("business_id"):
                business_id = user["business_id"]

    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authentication required. Please log in.")

    if not business_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No business profile selected.")

    # Auto-create a conversation session if none provided
    if not session_id:
        from app.db.tools.sessions import insert_session, find_active_session
        existing = await find_active_session(business_id, user_id)
        if existing:
            session_id = existing["id"]
        else:
            new_session = await insert_session(business_id, user_id, title="Voice Session")
            session_id = new_session["id"]
        logger.info(f"Voice session resolved: {session_id}")

    logger.info(f"Token request: business_id={business_id} session_id={session_id} user_id={user_id}")

    room_name = f"tendo-{business_id}"
    metadata = json.dumps({"business_id": business_id, "session_id": session_id, "user_id": user_id})

    try:
        async with LiveKitAPI() as api:
            from livekit.protocol.room import UpdateRoomMetadataRequest

            # Create or get room, then update metadata
            await api.room.create_room(CreateRoomRequest(
                name=room_name,
                metadata=metadata,
            ))

            # Always update metadata (create_room doesn't update existing rooms)
            try:
                await api.room.update_room_metadata(UpdateRoomMetadataRequest(
                    room=room_name,
                    metadata=metadata,
                ))
            except Exception:
                pass

            # Dispatch the agent to the room
            await api.agent_dispatch.create_dispatch(CreateAgentDispatchRequest(
                room=room_name,
                agent_name="tendo-voice",
                metadata=metadata,
            ))

            logger.info(f"Room created and agent dispatched: {room_name} metadata={metadata}")
    except Exception as e:
        logger.warning(f"Room/dispatch: {e}")

    token = (
        AccessToken(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        .with_identity(user_id)
        .with_name(user_id)
        .with_grants(VideoGrants(
            room_join=True,
            room=room_name,
        ))
        .with_metadata(metadata)
    )

    jwt = token.to_jwt()

    return {
        "token": jwt,
        "url": settings.livekit_url,
        "room": room_name,
    }
