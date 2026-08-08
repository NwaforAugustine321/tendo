import logging
from app.ws.socketio_server import emit_event, sio
from app.services.auth import handle_get_me, COOKIE_NAME
from app.graph.nodes.moa_orchestrator import moa_node

logger = logging.getLogger(__name__)

sessions: dict[str, dict] = {}


@sio.event
async def connect(sid, environ, auth):
   
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

    user_id = ""
    if token:
        user = await handle_get_me(token)
        if user:
            user_id = user["user_id"]

    sessions[sid] = {
        "session_id": session_id,
        "business_id": business_id,
        "user_id": user_id,
    }


@sio.event
async def message(sid, data):

    session = sessions.get(sid)
    if not  session:
        payload = {
            "type": "message", 
            "data": {
                "response": "Unauthorized", 
                }
            }
        await emit_event("message",payload=payload, sid=sid)
        return

    text = ""
    record_id = ""

    if isinstance(data, dict):

        if data.get("type") == "text":
            text = data.get("data", "")
        else:
            text = data.get("text", data.get("data", ""))

        record_id = data.get("record_id", "")

        if not data.get("business_id"):

            payload = {
                "type": "message", 
                "data": {
                "response": "Unauthorized, no bussiness id", 
                }
            }

            await emit_event("message",payload=payload, sid=sid)
            return 

        if not data.get("session_id"):

            payload = {
               "type": "message", 
               "data": {
                "response": "Unauthorized, no session id", 
                }
            }

            await emit_event("message",payload=payload, sid=sid)
            return

    else:
        payload = {
            "type": "message", 
            "data": {
                "response": "Invalid message format", 
                }
        }
        await emit_event("message",payload=payload, sid=sid)
        return      

    if not text.strip():
        return

    session_id = data["session_id"]
    business_id = data["business_id"]

    session["business_id"] = business_id
    session["session_id"]  = session_id
    user_id = session.get("user_id", ""),
    

    logger.info(f"Chat message from {sid}: {text[:100]}")

    async def _emit_event(event_name: str, payload: dict):
        await emit_event(event_name, payload=payload, sid=sid)

    try:

        graph_state = {
            "text": text,
            "record_id": record_id,
            "business_id": business_id,
            "thread_id": session_id,
            "session_id": session_id,
            "user_id": user_id,
            "emit_event": _emit_event
        }

        result = await moa_node(graph_state)
        response = result.get("response", {})


        await _emit_event("message", payload={
                "type": "message",
                "data": {"response": response.get("text", ""), "msg_type": response.get("msg_type", "answer")},
        })

    except Exception as e:
        logger.error(f"Chat error for {sid}: {e}", exc_info=True)
        await _emit_event("message",payload= {
            "type": "message",
            "data": {"response": "Something went wrong. Please try again.", "msg_type": "answer"},
        })


@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO disconnected: {sid}")
    sessions.pop(sid, None)


@sio.event
async def get_record_understanding(sid, data):
    """Handle request for record understanding via WebSocket."""
    from app.record_knowledge.record_agent import get_record_understanding as fetch_understanding

    session = sessions.get(sid)
    business_id = ""
    if session:
        business_id = session.get("business_id", "")

    if isinstance(data, dict):
        record_id = data.get("record_id", "")
        if data.get("business_id"):
            business_id = data["business_id"]
    else:
        record_id = ""

    if not record_id or not business_id:
        await emit_event("record_understanding",payload= {"insight": "", "suggestions": [], "record_id": record_id}, sid=sid)
        return

    try:
        result = await fetch_understanding(business_id, record_id)
        await emit_event("record_understanding", payload= {
            "record_id": record_id,
            "insight": result.get("insight", ""),
            "suggestions": result.get("suggestions", []),
        }, sid=sid)
    except Exception as e:
        logger.error(f"Error fetching understanding for {record_id}: {e}", exc_info=True)
        await emit_event(
          "record_understanding", 
          payload={"insight": "", "suggestions": [], "record_id": record_id},
          sid=sid
          )

