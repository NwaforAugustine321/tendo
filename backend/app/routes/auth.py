"""Auth routes — thin HTTP layer, delegates to auth service."""

from fastapi import APIRouter, Response, Request, HTTPException

from app.models.auth import RegisterRequest, LoginRequest, AuthResponse
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
    try:
        result = await handle_register(body.email, body.password, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    try:
        result = await handle_login(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

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
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")

    return AuthResponse(user_id=user["user_id"], email=user["email"], name=user["name"])
