from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.db.client import get_client


class AuthService:

    async def authenticate(
        self,
        request: Request,
    ) -> dict[str, Any]:
        authorization = request.headers.get(
            "Authorization",
            "",
        )

        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header is required.",
            )

        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header.",
            )

        try:
            supabase = get_supabase_client()

            response = supabase.auth.get_user(
                token,
            )

            user = response.user

        except Exception as exc:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authorization token.",
            ) from exc

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authorization token.",
            )

        return {
            "user_id": str(user.id),
        }


auth_service = AuthService()
