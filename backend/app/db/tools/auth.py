

import logging
from app.db.client import get_client

logger = logging.getLogger(__name__)

client = get_client()


async def register_user(email: str, password: str, name: str = "") -> dict:
    result = client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"name": name}} if name else {},
    })

    if hasattr(result, 'user') and result.user:
        return {
            "user_id": result.user.id,
            "email": result.user.email,
            "name": name,
            "access_token": result.session.access_token if result.session else "",
        }

    raise ValueError("Registration failed")


async def login_user(email: str, password: str) -> dict:

    result = client.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

    if hasattr(result, 'user') and result.user:
        return {
            "user_id": result.user.id,
            "email": result.user.email,
            "name": result.user.user_metadata.get("name", ""),
            "access_token": result.session.access_token if result.session else "",
        }

    raise ValueError("Invalid credentials")


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


async def send_password_reset_email(email: str, redirect_to: str = "") -> bool:
    """Send a password reset email via Supabase Auth."""
    try:
        options = {}
        if redirect_to:
            options["redirect_to"] = redirect_to
        client.auth.reset_password_email(email, options=options)
        return True
    except Exception:
        return False


async def update_user_password(access_token: str, new_password: str) -> bool:
    """Update a user's password using their access token."""
    try:
        client.auth.admin.update_user_by_id(
            _get_user_id_from_token(access_token),
            {"password": new_password},
        )
        return True
    except Exception:
        return False


def _get_user_id_from_token(access_token: str) -> str:
    """Extract user ID from token by verifying it."""
    result = client.auth.get_user(access_token)
    if result and result.user:
        return result.user.id
    raise ValueError("Invalid token")
