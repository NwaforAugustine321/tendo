"""Conversation routes — sessions and messages."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.lib.auth_dependency import get_current_user
from app.db.tools.sessions import insert_session, list_sessions, get_session, update_session_title
from app.db.tools.messages import fetch_messages

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateSessionRequest(BaseModel):
    business_id: str
    title: str = "New Session"
    record_id: str | None = None


class UpdateSessionRequest(BaseModel):
    title: str


@router.get("/sessions")
async def list_sessions_route(
    business_id: str = Query(...),
    record_id: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    """List all conversation sessions for a business."""
    return await list_sessions(business_id, user["user_id"], record_id=record_id)


@router.post("/sessions")
async def create_session_route(
    body: CreateSessionRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new conversation session."""
    return await insert_session(body.business_id, user["user_id"], body.title, record_id=body.record_id)


@router.get("/sessions/{session_id}")
async def get_session_route(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a single session by ID."""
    return await get_session(session_id)


@router.put("/sessions/{session_id}")
async def update_session_route(
    session_id: str,
    body: UpdateSessionRequest,
    user: dict = Depends(get_current_user),
):
    """Update session title."""
    return await update_session_title(session_id, body.title)


@router.get("/sessions/{session_id}/messages")
async def get_messages_route(
    session_id: str,
    business_id: str = Query(...),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    user: dict = Depends(get_current_user),
):
    """Fetch messages for a session with pagination."""
    import logging
    logger = logging.getLogger(__name__)
    messages = await fetch_messages(business_id, session_id, limit=limit, offset=offset)
    logger.info(f"[Conversations] fetch messages session={session_id}, business={business_id}, count={len(messages)}, offset={offset}")
    return [{"role": m["role"], "content": m["content"]} for m in messages]


@router.delete("/sessions/{session_id}")
async def delete_session_route(
    session_id: str,
    business_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Delete a session and its messages."""
    from app.db.client import get_client
    client = get_client()
    client.table("conversation_messages").delete().eq("session_id", session_id).eq("business_id", business_id).execute()
    client.table("conversation_sessions").delete().eq("id", session_id).eq("business_id", business_id).execute()
    return {"status": "deleted"}
