"""Auth routes — thin HTTP layer."""

from fastapi import APIRouter, Depends, Response

from app.models.auth import RegisterRequest, LoginRequest, AuthResponse, ForgotPasswordRequest, ResetPasswordRequest
from app.lib.auth_dependency import get_current_user
from app.services.auth import (
    handle_register,
    handle_login,
    handle_forgot_password,
    handle_reset_password,
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
            samesite="none",
            secure=True,
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
            samesite="none",
            secure=True,
        )

    return AuthResponse(user_id=result["user_id"], email=result["email"], name=result["name"])


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"status": "logged_out"}


@router.get("/me", response_model=AuthResponse)
async def me(user: dict = Depends(get_current_user)):
    return AuthResponse(user_id=user["user_id"], email=user["email"], name=user["name"])


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    result = await handle_forgot_password(body.email, body.redirect_to)
    return result


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    result = await handle_reset_password(body.access_token, body.new_password)
    return result


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
    }
