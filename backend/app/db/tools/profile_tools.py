"""Profile tools — business_id pre-baked via closure."""

import json
from langchain_core.tools import tool


def get_profile_tools(business_id: str) -> list:

    @tool
    async def get_business_profile() -> str:
        """Fetch the profile information about the business."""
        from app.db.tools.profiles import get_business_profile as _get_profile

        try:
            profile = await _get_profile(business_id=business_id)
            if profile and isinstance(profile, dict) and not profile.get("error"):
                exclude = {"id", "user_id", "created_at", "updated_at", "onboarding_completed", "logo_url"}
                data = {k: v for k, v in profile.items() if k not in exclude and v}
                return json.dumps(data, default=str) if data else "No results."
            return "No results."
        except Exception as e:
            return f"No results."

    return [get_business_profile]
