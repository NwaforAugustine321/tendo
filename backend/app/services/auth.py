

import logging

from app.db.tools.auth import register_user, login_user, get_user_by_token, send_password_reset_email, update_user_password
from app.db.tools.profiles import create_user_profile
from app.lib.errors import AuthError

logger = logging.getLogger(__name__)

COOKIE_NAME = "tendo_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7


async def handle_register(email: str, password: str, name: str) -> dict:
    try:
        result = await register_user(email, password, name)

        await create_user_profile(result["user_id"], email, name)

        return result
    except Exception as e:
        logger.error(f"Register failed: {e}")
        raise AuthError(
            "Could not create account. Email may already be in use.")


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


async def handle_forgot_password(email: str, redirect_to: str = "") -> dict:
    """Send a password reset email. Always returns success to prevent email enumeration."""
    try:
        await send_password_reset_email(email, redirect_to)
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
    # Always return success to avoid revealing if email exists
    return {"status": "sent"}


async def handle_reset_password(access_token: str, new_password: str) -> dict:
    """Reset the user's password using a valid access token."""
    try:
        success = await update_user_password(access_token, new_password)
        if not success:
            raise AuthError("Could not reset password. Token may be expired.")
        return {"status": "password_updated"}
    except AuthError:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise AuthError("Could not reset password. Please try again.")
