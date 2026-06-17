"""Business profile routes."""

from fastapi import APIRouter, Request

from app.lib.errors import AuthError
from app.services.auth import handle_get_me, COOKIE_NAME
from app.services.business import get_profiles

router = APIRouter(prefix="/business", tags=["business"])


@router.get("/profiles")
async def list_profiles(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    profiles = await get_profiles(user["user_id"])
    return {"profiles": profiles}
