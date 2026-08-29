"""Business profile routes — thin HTTP layer."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.lib.auth_dependency import get_current_user
from app.services.business import (
    list_profiles,
    get_profile,
    create_empty_profile,
    update_profile,
    delete_profile,
    resume_session,
)

router = APIRouter(prefix="/business", tags=["business"])


class ResumeSessionRequest(BaseModel):
    business_id: str


class UpdateProfileRequest(BaseModel):
    name: str = ""
    category: str = ""
    description: str = ""
    phone: str = ""
    location: str = ""
    metadata: dict | None = None
    onboarding_completed: bool = False


@router.get("/profiles")
async def get_profiles_route(user: dict = Depends(get_current_user)):
    profiles = await list_profiles(user["user_id"])
    return {"profiles": profiles}


@router.post("/create-empty")
async def create_empty_route(user: dict = Depends(get_current_user)):
    """Create an empty business profile + conversation session."""
    return await create_empty_profile(user["user_id"])


@router.post("/resume-session")
async def resume_session_route(body: ResumeSessionRequest, user: dict = Depends(get_current_user)):
    """Get or create a session for an existing business."""
    return await resume_session(body.business_id, user["user_id"])


@router.get("/profile/{business_id}")
async def get_profile_route(business_id: str, user: dict = Depends(get_current_user)):
    """Get a single business profile by ID."""
    profile = await get_profile(business_id)
    return {"profile": profile}


@router.put("/profile/{business_id}")
async def update_profile_route(
    business_id: str,
    body: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    """Update a business profile."""
    valid_fields = ("name", "category", "description", "phone", "location", "onboarding_completed")
    updates = {}
    for field in valid_fields:
        val = getattr(body, field, None)
        if val is None:
            continue
        if isinstance(val, bool):
            updates[field] = val
        elif val:
            updates[field] = val

    if body.metadata is not None:
        updates["metadata"] = body.metadata

    result = await update_profile(business_id, updates)
    return {"profile": result}


@router.delete("/profile/{business_id}")
async def delete_profile_route(business_id: str, user: dict = Depends(get_current_user)):
    """Delete an incomplete business profile."""
    return await delete_profile(business_id, user["user_id"])
