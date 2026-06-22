"""Business profile routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.lib.auth_dependency import get_current_user
from app.services.business import list_business_profiles, create_empty_business_profile
from app.services.session import create_session, get_or_create_session
from app.events.writer import EventWriter

router = APIRouter(prefix="/business", tags=["business"])

_event_writer = EventWriter()


class ResumeSessionRequest(BaseModel):
    business_id: str


@router.get("/profiles")
async def get_profiles(user: dict = Depends(get_current_user)):
    profiles = await list_business_profiles(user["user_id"])
    return {"profiles": profiles}


@router.post("/create-empty")
async def create_empty(user: dict = Depends(get_current_user)):
    """Create an empty business profile + conversation session."""
    user_id = user["user_id"]

    profile = await create_empty_business_profile(user_id)
    business_id = profile["id"]

    session = await create_session(business_id, user_id)
    session_id = session["id"]

    _event_writer.write(
        business_id=business_id,
        entity_type="business_profile",
        entity_id=business_id,
        event_type="BusinessProfileCreated",
        source="api",
        payload={"profile_id": business_id, "session_id": session_id},
        metadata={"user_id": user_id, "action": "create_empty"},
        session_id=session_id,
    )

    return {"business_id": business_id, "session_id": session_id}


@router.post("/resume-session")
async def resume_session(body: ResumeSessionRequest, user: dict = Depends(get_current_user)):
    """Get or create a session for an existing business (resume onboarding)."""
    session = await get_or_create_session(body.business_id, user["user_id"])
    return {"session_id": session["id"], "business_id": body.business_id}


@router.get("/profile/{business_id}")
async def get_profile(business_id: str, user: dict = Depends(get_current_user)):
    """Get a single business profile by ID."""
    from app.db.tools.profiles import get_business_profile
    profile = await get_business_profile(business_id)
    return {"profile": profile}


class UpdateProfileRequest(BaseModel):
    name: str = ""
    category: str = ""
    description: str = ""
    phone: str = ""
    location: str = ""
    metadata: dict | None = None
    onboarding_completed: bool = False


@router.put("/profile/{business_id}")
async def update_profile(
    business_id: str,
    body: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    """Update a business profile directly (from sidebar form)."""
    from app.db.client import get_client

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

    if not updates:
        return {"profile": {"error": "No valid fields to update"}}

    client = get_client()
    result = client.table("business_profiles").update(updates).eq("id", business_id).execute()

    _event_writer.write(
        business_id=business_id,
        entity_type="business_profile",
        entity_id=business_id,
        event_type="BusinessProfileUpdated",
        source="ui",
        payload=updates,
        metadata={"user_id": user["user_id"], "fields_changed": list(updates.keys())},
    )

    return {"profile": result.data[0] if result.data else {"error": "Update failed"}}


@router.delete("/profile/{business_id}")
async def delete_profile(business_id: str, user: dict = Depends(get_current_user)):
    """Delete an incomplete business profile. Cannot delete completed profiles."""
    from app.db.client import get_client
    client = get_client()

    profile = (
        client.table("business_profiles")
        .select("id, onboarding_completed")
        .eq("id", business_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )
    if not profile.data:
        return {"error": "Profile not found"}, 404

    if profile.data.get("onboarding_completed"):
        return {"error": "Cannot delete a completed business profile"}, 403

    client.table("conversation_sessions").delete().eq("business_id", business_id).execute()
    client.table("business_profiles").delete().eq("id", business_id).execute()

    _event_writer.write(
        business_id=business_id,
        entity_type="business_profile",
        entity_id=business_id,
        event_type="BusinessProfileDeleted",
        source="ui",
        payload={"profile_id": business_id},
        metadata={"user_id": user["user_id"], "action": "delete"},
    )

    return {"deleted": True}
