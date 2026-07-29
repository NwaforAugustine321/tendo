"""Socket.IO chat event handlers — bridges Socket.IO to the LangGraph workflow."""

import logging

from app.ws.socketio_server import sio
from app.services.auth import handle_get_me, COOKIE_NAME

logger = logging.getLogger(__name__)

_chat_sessions: dict[str, dict] = {}


@sio.event
async def connect(sid, environ, auth):
    logger.info(f"Socket.IO connected: {sid}")

    query_string = environ.get("QUERY_STRING", "")
    params = dict(p.split("=", 1) for p in query_string.split("&") if "=" in p)

    session_id = params.get("session_id", "")
    business_id = params.get("business_id", "")

    cookies = environ.get("HTTP_COOKIE", "")
    token = None
    for cookie in cookies.split(";"):
        cookie = cookie.strip()
        if cookie.startswith(f"{COOKIE_NAME}="):
            token = cookie[len(f"{COOKIE_NAME}="):]
            break

    user_id = "anonymous"
    if token:
        user = await handle_get_me(token)
        if user:
            user_id = user["user_id"]

    _chat_sessions[sid] = {
        "session_id": session_id,
        "business_id": business_id,
        "user_id": user_id,
    }


@sio.event
async def message(sid, data):
    from app.graph.workflow import get_graph

    session = _chat_sessions.get(sid)
    if not session:
        await sio.emit("message", {"type": "message", "data": {"response": "Session not found", "msg_type": "answer"}}, to=sid)
        return

    text = ""
    record_id = ""
    scopes = None
    if isinstance(data, dict):
        if data.get("type") == "text":
            text = data.get("data", "")
        else:
            text = data.get("text", data.get("data", ""))
        raw_scope = data.get("scope", None)
        if isinstance(raw_scope, list):
            scopes = raw_scope
        elif raw_scope:
            scopes = [raw_scope]
        record_id = data.get("record_id", "")
        if data.get("business_id"):
            session["business_id"] = data["business_id"]
        if data.get("session_id"):
            session["session_id"] = data["session_id"]
    else:
        text = str(data)

    if not text.strip():
        return

    business_id = session.get("business_id", "")
    
    if not business_id:
        return

    logger.info(f"Chat message from {sid}: {text[:100]} [scopes={scopes}]")

    session_id = session.get("session_id", "")

    async def emit_callback(event_name: str, payload: dict):
        await sio.emit(event_name, payload, to=sid)

    try:
        graph_state = {
            "event": {
                "text": text,
                "business_id": business_id,
                "thread_id": session_id,
                "record_id": record_id,
                "scopes": scopes,
            },
            "business_id": business_id,
            "thread_id": session_id,
            "emit_callback": emit_callback,
        }

        graph = get_graph()
        await graph.ainvoke(graph_state)

    except Exception as e:
        logger.error(f"Chat error for {sid}: {e}", exc_info=True)
        await sio.emit("message", {
            "type": "message",
            "data": {"response": "Something went wrong. Please try again.", "msg_type": "answer"},
        }, to=sid)


@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO disconnected: {sid}")
    _chat_sessions.pop(sid, None)
