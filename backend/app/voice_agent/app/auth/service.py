
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from ..db.client import get_client

client = get_client()

COOKIE_NAME = "tendo_session"


async def get_user_by_token(access_token: str) -> dict | None:

    try:
        result = client.auth.get_user(access_token)
        if result and result.user:
            return {
                "user_id": result.user.id,
                "email": result.user.email,
                "name": result.user.user_metadata.get("name", ""),
            }
    except Exception:
        pass
    return None


class AuthService:

    async def authenticate(
        self,
        request: Request,
    ) -> dict[str, Any]:
        token = request.cookies.get(COOKIE_NAME)

        if not token:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated.",
            )

        try:
            user = await get_user_by_token(token)
        except Exception as exc:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session.",
            ) from exc

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Session expired.",
            )

        return user


auth_service = AuthService()
