"""Profile tools — LangChain tool wrappers for profile db operations."""

import json

from langchain_core.tools import tool


@tool
async def get_business_profile(business_id: str) -> str:
    """Get the current business profile (name, category, description, phone, location, metadata). Use this to check what's known about the business."""
    from app.db.tools.profiles import get_business_profile as _get_profile

    try:
        profile = await _get_profile(business_id=business_id)
        if profile and isinstance(profile, dict) and not profile.get("error"):
            exclude = {"id", "user_id", "created_at", "updated_at", "onboarding_completed", "logo_url"}
            data = {k: v for k, v in profile.items() if k not in exclude and v}
            return json.dumps(data, default=str) if data else "Profile exists but has no data yet."
        return "No business profile found."
    except Exception as e:
        return f"Could not retrieve profile: {e}"
