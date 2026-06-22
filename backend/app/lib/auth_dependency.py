"""Authentication dependency for FastAPI routes."""

from fastapi import Request

from app.lib.errors import AuthError
from app.services.auth import handle_get_me, COOKIE_NAME


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency that extracts and validates the authenticated user.

    Usage:
        @router.get("/endpoint")
        async def my_route(user: dict = Depends(get_current_user)):
            ...

    Raises AuthError if no valid session found.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    return user
