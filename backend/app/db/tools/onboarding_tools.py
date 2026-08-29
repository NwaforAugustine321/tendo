"""Onboarding tools — business_id pre-baked via closure."""

import json
from langchain_core.tools import tool
from app.db.tools.profiles import get_business_profile, update_business_profile


def get_onboarding_tools(business_id: str) -> list:

    @tool
    async def fetch_business_profile() -> dict:
        """Fetch the current business profile."""
        result = await get_business_profile(business_id)
        if not result:
            return {"content": "No results.", "metadata": {}, "images": [], "videos": [], "audios": []}
        exclude = {"id", "user_id", "created_at", "updated_at", "onboarding_completed", "logo_url"}
        data = {k: v for k, v in result.items() if k not in exclude and v}
        if not data:
            return {"content": "No results.", "metadata": {}, "images": [], "videos": [], "audios": []}
        return {"content": json.dumps(data, default=str), "metadata": data, "images": [], "videos": [], "audios": []}

    @tool
    async def update_profile(name: str = "", category: str = "", description: str = "", phone: str = "", location: str = "", logo_url: str = "") -> dict:
        """Update the business profile with provided fields."""
        kwargs = {}
        if name: kwargs["name"] = name
        if category: kwargs["category"] = category
        if description: kwargs["description"] = description
        if phone: kwargs["phone"] = phone
        if location: kwargs["location"] = location
        if logo_url: kwargs["logo_url"] = logo_url
        if not kwargs:
            return {"content": "No fields provided to update.", "metadata": {}, "images": [], "videos": [], "audios": []}
        result = await update_business_profile(business_id, **kwargs)
        if not result:
            return {"content": "No results.", "metadata": {}, "images": [], "videos": [], "audios": []}
        return {"content": json.dumps(result, default=str), "metadata": result, "images": [], "videos": [], "audios": []}

    return [fetch_business_profile, update_profile]
