"""Profile database operations."""

import logging
from app.db.client import get_client

logger = logging.getLogger(__name__)


async def create_user_profile(user_id: str, email: str, name: str = "") -> dict:
    client = get_client()
    data = {"id": user_id, "email": email, "name": name}
    result = client.table("user_profiles").insert(data).execute()
    return result.data[0] if result.data else data


async def get_user_profile(user_id: str) -> dict | None:
    client = get_client()
    result = client.table("user_profiles").select("*").eq("id", user_id).single().execute()
    return result.data if result.data else None


async def get_business_profiles(user_id: str) -> list[dict]:
    client = get_client()
    result = client.table("business_profiles").select("*").eq("user_id", user_id).execute()
    return result.data or []
