"""Socket.IO chat event handlers — bridges Socket.IO to the MOA Orchestrator."""

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
    from app.graph.nodes.moa_orchestrator import moa_orchestrator

    session = _chat_sessions.get(sid)
    if not session:
        await sio.emit("message", {"type": "message", "data": {"response": "Session not found", "msg_type": "answer"}}, to=sid)
        return

    text = ""
    scope = "knowledge"
    record_id = ""
    scopes = None
    if isinstance(data, dict):
        if data.get("type") == "text":
            text = data.get("data", "")
        else:
            text = data.get("text", data.get("data", ""))
        raw_scope = data.get("scope", None)
        if isinstance(raw_scope, list):
            scope = raw_scope[0] if raw_scope else None
            scopes = raw_scope
        else:
            scope = raw_scope
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
        await sio.emit("message", {"type": "message", "data": {"response": "No business context. Please reconnect.", "msg_type": "answer"}}, to=sid)
        return

    logger.info(f"Chat message from {sid}: {text[:100]} [scope={scope}]")

    # Build scopes from record_id if no explicit scopes provided
    if scopes is None and record_id:
        scopes = [f"/{business_id}/record/{record_id}", f"/business/{business_id}"]

    async def thinking_callback(msg):
        if isinstance(msg, dict):
            thinking_text = msg.get("data", str(msg))
        else:
            thinking_text = str(msg)
        await sio.emit("message", {"type": "thinking", "data": thinking_text}, to=sid)

    try:
        # Fetch recent conversation from LanceDB (semantic + recent)
        conversation_messages = []
        session_id = session.get("session_id", "")
        if session_id and business_id:
            from app.memory.memory import Memory
            try:
                conv_memory = Memory(scopes=[f"/business/{business_id}/conversations/{session_id}"], business_id=business_id)
                recent = await conv_memory.recall(query=text, limit=8)
                if recent:
                    for r in recent:
                        meta = r.metadata or {}
                        conversation_messages.append({"role": meta.get("role", "user"), "content": r.content})
            except Exception:
                pass

        result = await moa_orchestrator(
            user_request=text,
            business_id=business_id,
            thinking_callback=thinking_callback,
            conversation_messages=conversation_messages,
            scope=scope,
            record_id=record_id,
            scopes=scopes,
        )

        response = result.get("response", "")
        if isinstance(response, dict):
            response_text = response.get("text", response.get("response", ""))
        else:
            response_text = str(response)

        if not response_text:
            response_text = "I'm here to help. What would you like to know?"

        # Detect if the agent is waiting for user input (questions/fields)
        is_waiting = False
        questions = None
        try:
            from app.lib.json_parser import parse_json_output
            parsed = parse_json_output(response_text) if response_text.strip().startswith('{') else None
            if parsed and isinstance(parsed, dict):
                if parsed.get("workflow_status") == "waiting_for_user" or parsed.get("fields"):
                    is_waiting = True
                    questions = parsed.get("fields", [])
                    response_text = parsed.get("response", response_text)
        except Exception:
            pass

        # Save messages to LanceDB (fast retrieval) and DB (long-term)
        session_id = session.get("session_id", "")
        if session_id and business_id:
            from app.memory.memory import Memory
            from app.db.tools.messages import save_messages

            conv_scope = f"/business/{business_id}/conversations/{session_id}"
            try:
                conv_memory = Memory(scopes=[conv_scope], business_id=business_id)
                await conv_memory.remember(content=text, metadata={"role": "user", "session_id": session_id})
                assistant_meta = {"role": "assistant", "session_id": session_id}
                if is_waiting:
                    assistant_meta["waiting_for_user"] = True
                    if questions:
                        assistant_meta["questions"] = questions
                await conv_memory.remember(content=response_text, metadata=assistant_meta)
            except Exception:
                pass

            # Long-term DB persistence
            await save_messages(business_id, session_id, [
                {"role": "user", "content": text},
                {"role": "assistant", "content": response_text},
            ])

        logger.info(f"Sending response to {sid}: {response_text[:100]}")
        if is_waiting and questions:
            await sio.emit("message", {
                "type": "message",
                "data": {"response": response_text, "msg_type": "question", "questions": questions},
            }, to=sid)
        else:
            await sio.emit("message", {
                "type": "message",
                "data": {"response": response_text, "msg_type": "answer"},
            }, to=sid)

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
