"""Profile database operations with event emission."""

import logging

from app.db.client import get_client


logger = logging.getLogger(__name__)


async def create_user_profile(user_id: str, email: str, name: str = "") -> dict:
    """Create a user profile."""
    client = get_client()
    data = {"id": user_id, "email": email, "name": name}
    result = client.table("user_profiles").insert(data).execute()
    return result.data[0] if result.data else data


async def get_user_profile(user_id: str) -> dict | None:
    """Get a user profile by ID."""
    client = get_client()
    result = client.table("user_profiles").select(
        "*").eq("id", user_id).single().execute()
    return result.data if result.data else None


async def get_business_profiles(user_id: str) -> list[dict]:
    """Get all business profiles for a user."""
    client = get_client()
    result = client.table("business_profiles").select(
        "*").eq("user_id", user_id).execute()
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
    if not result.data:
        raise Exception("Failed to insert empty business profile")

    profile = result.data[0]

    return profile


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
    profile = result.data[0] if result.data else data

    if result.data:
        pass
    return profile


async def get_business_profile(business_id: str, **kwargs) -> dict:
    """Get a business profile by ID."""
    client = get_client()
    result = client.table("business_profiles").select(
        "*").eq("id", business_id).single().execute()
    return result.data if result.data else {"error": "Not found"}


async def update_business_profile(business_id: str, **kwargs) -> dict:
    """Update a business profile. Only updates fields with non-empty values. Merges metadata."""
    client = get_client()
    valid_fields = ("name", "category", "description", "metadata",
                    "phone", "location", "logo_url", "onboarding_completed")
    updates = {}
    for k, v in kwargs.items():
        if k not in valid_fields:
            continue
        if isinstance(v, bool):
            updates[k] = v
        elif isinstance(v, dict) and k == "metadata":
            try:
                existing = client.table("business_profiles").select(
                    "metadata").eq("id", business_id).execute()
                existing_meta = (existing.data[0].get(
                    "metadata") or {}) if existing.data else {}
                merged = {**existing_meta, **v}
                updates[k] = merged
            except Exception:
                updates[k] = v
        elif v:
            updates[k] = v

    if not updates:
        return {"error": "No valid fields to update"}

    result = client.table("business_profiles").update(
        updates).eq("id", business_id).execute()

    if result.data:
        pass

    return result.data[0] if result.data else {"error": "Update failed"}


async def delete_business_profile(business_id: str, user_id: str) -> dict:
    """Delete an incomplete business profile and its sessions."""
    client = get_client()
    profile = client.table("business_profiles").select("id, onboarding_completed").eq(
        "id", business_id).eq("user_id", user_id).single().execute()
    if not profile.data:
        return {"error": "Profile not found"}
    if profile.data.get("onboarding_completed"):
        return {"error": "Cannot delete a completed business profile"}

    client.table("conversation_sessions").delete().eq(
        "business_id", business_id).execute()
    client.table("business_profiles").delete().eq("id", business_id).execute()

    return {"deleted": True}
