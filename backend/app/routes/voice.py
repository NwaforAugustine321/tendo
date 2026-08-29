"""Voice routes — thin HTTP layer."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from livekit.api import AccessToken, VideoGrants

from app.communication.event_bus import get_event_bus
from app.config.settings import settings
from app.lib.auth_dependency import get_current_user
from app.services.voice import voice_service

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "/voice/start/agent",
)
async def start_voice_agent(
    request: Request,
    user: dict = Depends(
        get_current_user,
    ),
):
    """
    Initialize a voice session and return a LiveKit token.

    The route is responsible only for HTTP-level concerns.

    Voice session business logic and EventBus publishing are delegated
    to VoiceService.
    """

    body: dict[str, Any] = await request.json()

    user_id = user["user_id"]

    business_id = (
        body.get(
            "business_id",
            "",
        )
        or user.get(
            "business_id",
            "",
        )
    )

    if not business_id:
        raise HTTPException(
            status_code=400,
            detail="No business profile selected.",
        )

    session_id = await voice_service.resolve_session(
        business_id=business_id,
        user_id=user_id,
        session_id=body.get(
            "session_id",
            "",
        ),
    )

    room_name = (
        f"tendo-{user_id}"
    )

    record_id = body.get(
        "record_id",
        "",
    )

    payload: dict[str, Any] = {
        "business_id": business_id,
        "session_id": session_id,
        "user_id": user_id,
        "room": room_name,
        "record_id": record_id,
    }

    metadata = json.dumps(
        payload,
    )

    logger.info(
        "Initializing voice session: "
        "room=%s business_id=%s session_id=%s "
        "user_id=%s record_id=%s",
        room_name,
        business_id,
        session_id,
        user_id,
        record_id,
    )

    try:

        await voice_service.ensure_room(
            room_name=room_name,
            metadata=metadata,
        )

        event_bus = get_event_bus()

        await voice_service.request_session(
            event_bus=event_bus,
            payload=payload,
        )

    except Exception as exc:
        logger.error(
            "Voice initialization failed: %s",
            exc,
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to initialize voice session. "
                "Please try again."
            ),
        ) from exc

    token = (
        AccessToken(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        .with_identity(
            user_id,
        )
        .with_name(
            user_id,
        )
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
            ),
        )
        .with_metadata(
            metadata,
        )
        .to_jwt()
    )

    return {
        "token": token,
        "url": settings.livekit_url,
        "room": room_name,
        "session_id": session_id,
        "business_id": business_id,
        "record_id": record_id,
    }


@router.post(
    "/voice/stop/agent",
)
async def stop_voice_agent(
    request: Request,
    user: dict = Depends(
        get_current_user,
    ),
):
    """
    Request the active voice session to stop.

    The actual LiveKit lifecycle operation is handled by the
    voice lifecycle service.
    """

    body: dict[str, Any] = await request.json()

    room_name = body.get(
        "room",
        "",
    )

    session_id = body.get(
        "session_id",
        "",
    )

    # -----------------------------------------------------------------------
    # Validate request
    # -----------------------------------------------------------------------

    if not room_name:
        raise HTTPException(
            status_code=400,
            detail="Room name is required.",
        )

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID is required.",
        )

    user_id = user["user_id"]

    # -----------------------------------------------------------------------
    # Build lifecycle payload
    # -----------------------------------------------------------------------

    payload: dict[str, Any] = {
        "room": room_name,
        "user_id": user_id,
        "session_id": session_id,
        "business_id": body.get(
            "business_id",
            "",
        ),
        "record_id": body.get(
            "record_id",
            "",
        ),
    }

    try:
        # -------------------------------------------------------------------
        # Publish stop request
        # -------------------------------------------------------------------

        event_bus = get_event_bus()

        await voice_service.stop_session(
            event_bus=event_bus,
            payload=payload,
        )

    except Exception as exc:
        logger.error(
            "Voice stop request failed: %s",
            exc,
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to stop voice session.",
        ) from exc

    logger.info(
        "Voice session stop requested: "
        "room=%s user_id=%s session_id=%s",
        room_name,
        user_id,
        session_id,
    )

    return {
        "status": "stop_requested",
        "session_id": session_id,
    }
