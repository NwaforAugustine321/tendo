

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from livekit.api import AccessToken, VideoGrants

from app.config.settings import settings
from app.lib.auth_dependency import get_current_user
from app.services.voice import voice_service

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "/voice/init/agent",
)
async def start_voice_agent(
    request: Request,
    user: dict = Depends(
        get_current_user,
    ),
):

    body: dict[str, Any] = await request.json()

    user_id = user["user_id"]

    business_id = (
        body.get(
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

    if not session_id:
        raise HTTPException(
            status_code=404,
            detail="No active session found.",
        )

    room_name = f"tendo-{business_id}"

    try:

        livekit_token = (
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

            .to_jwt()
        )

        await voice_service.create_voice_session(
            session_id=session_id,
            user_id=user_id,
            business_id=business_id,
            room=room_name,
            livekit_url=settings.livekit_url,
            livekit_token=livekit_token,
            token=livekit_token,
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

    return {
        "token": livekit_token,
        "url": settings.livekit_url,
        "room": room_name,
        "session_id": session_id,
        "business_id": business_id,
    }
