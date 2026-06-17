"""Auth routes — thin HTTP layer."""

from fastapi import APIRouter, Response, Request

from app.models.auth import RegisterRequest, LoginRequest, AuthResponse
from app.errors import AuthError
from app.services.auth import (
    handle_register,
    handle_login,
    handle_get_me,
    COOKIE_NAME,
    COOKIE_MAX_AGE,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, response: Response):
    result = await handle_register(body.email, body.password, body.name)

    if result.get("access_token"):
        response.set_cookie(
            key=COOKIE_NAME,
            value=result["access_token"],
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )

    return AuthResponse(user_id=result["user_id"], email=result["email"], name=result["name"])


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response):
    result = await handle_login(body.email, body.password)

    if result.get("access_token"):
        response.set_cookie(
            key=COOKIE_NAME,
            value=result["access_token"],
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )

    return AuthResponse(user_id=result["user_id"], email=result["email"], name=result["name"])


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"status": "logged_out"}


@router.get("/me", response_model=AuthResponse)
async def me(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired. Please log in again.")

    return AuthResponse(user_id=user["user_id"], email=user["email"], name=user["name"])
