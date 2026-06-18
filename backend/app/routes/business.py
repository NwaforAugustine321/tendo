"""Business profile routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.lib.errors import AuthError
from app.services.auth import handle_get_me, COOKIE_NAME
from app.services.business import list_business_profiles, create_empty_business_profile
from app.services.session import create_session, get_or_create_session

router = APIRouter(prefix="/business", tags=["business"])


class ResumeSessionRequest(BaseModel):
    business_id: str


@router.get("/profiles")
async def get_profiles(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    profiles = await list_business_profiles(user["user_id"])
    return {"profiles": profiles}


@router.post("/create-empty")
async def create_empty(request: Request):
    """Create an empty business profile + conversation session.
    
    Returns business_id and session_id for the onboarding flow.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    user_id = user["user_id"]

    # Create empty business profile
    profile = await create_empty_business_profile(user_id)
    business_id = profile["id"]

    # Create conversation session linked to this business
    session = await create_session(business_id, user_id)
    session_id = session["id"]

    return {"business_id": business_id, "session_id": session_id}


@router.post("/resume-session")
async def resume_session(request: Request, body: ResumeSessionRequest):
    """Get or create a session for an existing business (resume onboarding)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    user_id = user["user_id"]
    session = await get_or_create_session(body.business_id, user_id)

    return {"session_id": session["id"], "business_id": body.business_id}


@router.get("/profile/{business_id}")
async def get_profile(business_id: str, request: Request):
    """Get a single business profile by ID."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    from app.db.tools.profiles import get_business_profile
    profile = await get_business_profile(business_id)
    return {"profile": profile}


@router.delete("/profile/{business_id}")
async def delete_profile(business_id: str, request: Request):
    """Delete an incomplete business profile. Cannot delete completed profiles."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    from app.db.client import get_client
    client = get_client()

    # Check if profile exists and is incomplete
    profile = client.table("business_profiles").select("id, onboarding_completed").eq("id", business_id).eq("user_id", user["user_id"]).single().execute()
    if not profile.data:
        return {"error": "Profile not found"}, 404

    if profile.data.get("onboarding_completed"):
        return {"error": "Cannot delete a completed business profile"}, 403

    # Delete associated sessions first (FK constraint)
    client.table("conversation_sessions").delete().eq("business_id", business_id).execute()
    # Delete the profile
    client.table("business_profiles").delete().eq("id", business_id).execute()

    return {"deleted": True}
