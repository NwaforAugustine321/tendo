"""Onboarding tools — business_id pre-baked via closure."""

import json
from langchain_core.tools import tool
from app.db.tools.profiles import get_business_profile, update_business_profile


def get_onboarding_tools(business_id: str) -> list:

    @tool
    async def fetch_business_profile() -> str:
        """Fetch the current business profile."""
        result = await get_business_profile(business_id)
        if not result:
            return "No results."
        exclude = {"id", "user_id", "created_at", "updated_at", "onboarding_completed", "logo_url"}
        data = {k: v for k, v in result.items() if k not in exclude and v}
        return json.dumps(data, default=str) if data else "No results."

    @tool
    async def update_profile(name: str = "", category: str = "", description: str = "", phone: str = "", location: str = "", logo_url: str = "") -> str:
        """Update the business profile with provided fields."""
        kwargs = {}
        if name: kwargs["name"] = name
        if category: kwargs["category"] = category
        if description: kwargs["description"] = description
        if phone: kwargs["phone"] = phone
        if location: kwargs["location"] = location
        if logo_url: kwargs["logo_url"] = logo_url
        if not kwargs:
            return "No fields provided to update."
        result = await update_business_profile(business_id, **kwargs)
        if not result:
            return "No results."
        return json.dumps(result, default=str)

    return [fetch_business_profile, update_profile]
