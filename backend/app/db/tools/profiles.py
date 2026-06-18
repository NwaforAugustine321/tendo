"""Profile database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


async def create_user_profile(user_id: str, email: str, name: str = "") -> dict:
    """Create a user profile (used by auth service)."""
    client = get_client()
    data = {"id": user_id, "email": email, "name": name}
    result = client.table("user_profiles").insert(data).execute()
    return result.data[0] if result.data else data




async def get_user_profile(user_id: str) -> dict | None:
    """Get a user profile by ID."""
    client = get_client()
    result = client.table("user_profiles").select("*").eq("id", user_id).single().execute()
    return result.data if result.data else None


async def get_business_profiles(user_id: str) -> list[dict]:
    """Get all business profiles for a user."""
    client = get_client()
    result = client.table("business_profiles").select("*").eq("user_id", user_id).execute()
    return result.data or []


async def insert_empty_business_profile(user_id: str) -> dict:
    """Insert an empty business profile row with defaults."""
    client = get_client()
    data = {
        "user_id": user_id,
        "name": "",
        "category": "hybrid",
        "description": "",
        "phone": "",
        "location": "",
        "logo_url": "",
        "onboarding_completed": False,
    }
    result = client.table("business_profiles").insert(data).execute()
    if result.data:
        return result.data[0]
    raise Exception("Failed to insert empty business profile")


@register("create_business_profile")
async def create_business_profile(
    user_id: str, name: str, category: str = "hybrid", description: str = "",
    phone: str = "", location: str = "", logo_url: str = "", **kwargs
) -> dict:
    """Create a new business profile."""
    client = get_client()
    data = {
        "user_id": user_id,
        "name": name,
        "category": category,
        "description": description,
        "phone": phone,
        "location": location,
        "logo_url": logo_url,
        "metadata": kwargs.get("metadata", {}),
    }
    result = client.table("business_profiles").insert(data).execute()
    return result.data[0] if result.data else data


@register("get_business_profile")
async def get_business_profile(business_id: str, **kwargs) -> dict:
    """Get a business profile by ID."""
    client = get_client()
    result = client.table("business_profiles").select("*").eq("id", business_id).single().execute()
    return result.data if result.data else {"error": "Not found"}


@register("update_business_profile")
async def update_business_profile(business_id: str, **kwargs) -> dict:
    """Update a business profile."""
    client = get_client()
    valid_fields = ("name", "category", "description", "metadata", "phone", "location", "logo_url", "onboarding_completed")
    updates = {k: v for k, v in kwargs.items() if k in valid_fields}
    if not updates:
        return {"error": "No valid fields to update"}
    result = client.table("business_profiles").update(updates).eq("id", business_id).execute()
    return result.data[0] if result.data else {"error": "Update failed"}
