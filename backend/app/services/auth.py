"""Auth service."""

import logging

from app.db.tools.auth import register_user, login_user, get_user_by_token
from app.lib.errors import AuthError

logger = logging.getLogger(__name__)

COOKIE_NAME = "tendo_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7


async def handle_register(email: str, password: str, name: str) -> dict:
    try:
        return await register_user(email, password, name)
    except Exception as e:
        logger.error(f"Register failed: {e}")
        raise AuthError("Could not create account. Email may already be in use.")


async def handle_login(email: str, password: str) -> dict:
    try:
        return await login_user(email, password)
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise AuthError("Invalid email or password")


async def handle_get_me(token: str) -> dict | None:
    if not token:
        return None
    try:
        return await get_user_by_token(token)
    except Exception as e:
        logger.error(f"Session check failed: {e}")
        return None
