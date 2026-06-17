"""Auth service — business logic for authentication."""

import logging

from app.db.tools.auth import register_user, login_user, get_user_by_token

logger = logging.getLogger(__name__)

COOKIE_NAME = "tendo_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


async def handle_register(email: str, password: str, name: str) -> dict:
    """Register a new user. Returns user data + access token."""
    try:
        return await register_user(email, password, name)
    except ValueError as e:
        raise e
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise ValueError("Registration failed. Email may already be in use.")


async def handle_login(email: str, password: str) -> dict:
    """Authenticate a user. Returns user data + access token."""
    try:
        return await login_user(email, password)
    except ValueError:
        raise ValueError("Invalid email or password")
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise ValueError("Login failed")


async def handle_get_me(token: str) -> dict | None:
    """Get user from session token. Returns None if invalid."""
    return await get_user_by_token(token)
