"""Auth routes — register, login, logout, session check."""

import logging

from fastapi import APIRouter, Response, Request, HTTPException

from app.db.tools.auth import register_user, login_user, get_user_by_token
from app.models.auth import RegisterRequest, LoginRequest, AuthResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "tendo_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, response: Response):
    """Register a new user and set session cookie."""
    try:
        result = await register_user(body.email, body.password, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=400, detail="Registration failed. Email may already be in use.")

    # Set session cookie
    if result.get("access_token"):
        response.set_cookie(
            key=COOKIE_NAME,
            value=result["access_token"],
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,  # Set True in production with HTTPS
        )

    return AuthResponse(
        user_id=result["user_id"],
        email=result["email"],
        name=result["name"],
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response):
    """Login and set session cookie."""
    try:
        result = await login_user(body.email, body.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail="Login failed")

    if result.get("access_token"):
        response.set_cookie(
            key=COOKIE_NAME,
            value=result["access_token"],
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )

    return AuthResponse(
        user_id=result["user_id"],
        email=result["email"],
        name=result["name"],
    )


@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie(key=COOKIE_NAME)
    return {"status": "logged_out"}


@router.get("/me", response_model=AuthResponse)
async def me(request: Request):
    """Get current user from session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")

    return AuthResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
    )
