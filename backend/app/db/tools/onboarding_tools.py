"""LangChain tool wrappers for onboarding DB operations.

These are the @tool-decorated functions that the onboarding agent uses directly.
They wrap the plain functions in app/db/tools/profiles.py.
"""

import json

from langchain_core.tools import tool


@tool
async def fetch_business_profile(business_id: str) -> str:
    """Fetch the current business profile."""
    from app.db.tools.profiles import get_business_profile
    result = await get_business_profile(business_id)
    return json.dumps(result, default=str)


@tool
async def update_profile(business_id: str, name: str = "", category: str = "", description: str = "", phone: str = "", location: str = "", logo_url: str = "") -> str:
    """Update the business profile with provided fields."""
    from app.db.tools.profiles import update_business_profile
    kwargs = {}
    if name:
        kwargs["name"] = name
    if category:
        kwargs["category"] = category
    if description:
        kwargs["description"] = description
    if phone:
        kwargs["phone"] = phone
    if location:
        kwargs["location"] = location
    if logo_url:
        kwargs["logo_url"] = logo_url
    result = await update_business_profile(business_id, **kwargs)
    return json.dumps(result, default=str)


ONBOARDING_TOOLS = [fetch_business_profile, update_profile]
