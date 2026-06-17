"""Business profile routes."""

from fastapi import APIRouter, Request

from app.lib.errors import AuthError
from app.services.auth import handle_get_me, COOKIE_NAME
from app.services.business import list_business_profiles

router = APIRouter(prefix="/business", tags=["business"])


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


@router.post("/onboarding/start")
async def start_onboarding(request: Request):
    """Trigger the onboarding agent's first message."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthError("Not authenticated")

    user = await handle_get_me(token)
    if not user:
        raise AuthError("Session expired")

    from app.graph.nodes.moa import moa_node
    from app.graph.nodes.onboarding import onboarding_node

    state = {
        "event": {"text": "hello", "thread_id": "default", "business_id": "default"},
        "messages": [],
    }

    result = await moa_node(state)
    routed = result.get("routed_domain")
    if routed == "onboarding":
        result = await onboarding_node({**state, "messages": result.get("messages", [])})

    text = result.get("response", {}).get("text", "")

    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^[-*#]+\s*', '', text, flags=re.MULTILINE)

    return {"message": text}
