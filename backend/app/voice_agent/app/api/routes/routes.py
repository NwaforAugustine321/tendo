from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.service import auth_service
from ...services.voice_agent_service import voice_agent_service


router = APIRouter(
    prefix="/agent",
)


@router.post(
    "/start",
)
async def start_agent(
    request: Request,
    user: dict[str, Any] = Depends(
        auth_service.authenticate,
    ),
) -> dict[str, Any]:
    body: dict[str, Any] = await request.json()

    business_id = body.get(
        "business_id",
        "",
    )

    session_id = body.get(
        "session_id",
        "",
    )

    if not business_id:
        raise HTTPException(
            status_code=400,
            detail="Business ID is required.",
        )

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID is required.",
        )

    try:
        return await voice_agent_service.start(
            business_id=business_id,
            user_id=user["user_id"],
            session_id=session_id,
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to start voice agent.",
        ) from exc


# ================================================================
# STOP
# ================================================================


@router.post(
    "/stop",
)
async def stop_agent(
    request: Request,
    user: dict[str, Any] = Depends(
        auth_service.authenticate,
    ),
) -> dict[str, Any]:
    body: dict[str, Any] = await request.json()

    business_id = body.get(
        "business_id",
        "",
    )

    session_id = body.get(
        "session_id",
        "",
    )

    if not business_id:
        raise HTTPException(
            status_code=400,
            detail="Business ID is required.",
        )

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID is required.",
        )

    try:
        return await voice_agent_service.stop(
            business_id=business_id,
            user_id=user["user_id"],
            session_id=session_id,
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to stop voice agent.",
        ) from exc


# ================================================================
# SESSION STATUS
# ================================================================


@router.get(
    "/session/status",
)
async def session_status(
    request: Request,
    user: dict[str, Any] = Depends(
        auth_service.authenticate,
    ),
) -> dict[str, Any]:
    business_id = request.query_params.get(
        "business_id",
        "",
    )

    session_id = request.query_params.get(
        "session_id",
        "",
    )

    if not business_id:
        raise HTTPException(
            status_code=400,
            detail="Business ID is required.",
        )

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID is required.",
        )

    try:
        return await voice_agent_service.session_status(
            business_id=business_id,
            user_id=user["user_id"],
            session_id=session_id,
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to get agent session status.",
        ) from exc
