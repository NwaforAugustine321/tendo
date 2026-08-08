import asyncio
import logging
from typing import Any

from app.db.tools.messages import save_messages
from app.memory.memory import Memory

logger = logging.getLogger(__name__)

_planner = None


def _get_planner():
    global _planner
    if _planner is None:
        from app.planner import Planner
        _planner = Planner()
    return _planner


async def moa_orchestrator_node(state: dict) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    session_id = state.get("session_id") or event.get("session_id", "")
    record_id = event.get("record_id", "")
    scopes = event.get("scopes")
    emit_callback = state.get("emit_callback")
    user_id = state.get("user_id") or "anonymous"

    if not session_id and business_id:
        from app.db.tools.sessions import insert_session
        try:
            title = user_message[:50] if user_message else "Voice Session"
            new_session = await insert_session(business_id, user_id, title=title)
            session_id = new_session.get("id", "")
        except Exception as e:
            logger.warning(f"Failed to auto-create session: {e}")

    async def save_msg(messages):
        if not session_id:
            return
        await save_messages(business_id, session_id, messages, record_id=record_id or None)

    conversation_scope_id = session_id
    conversation_history = []
    try:
        memory = Memory(
            scopes=[f"/conversations/{conversation_scope_id}"],
            business_id=business_id,
            table_name="conversations",
        )
        recent = await memory.fetch(limit=10)
        if recent:
            for r in recent:
                meta = r.metadata or {}
                conversation_history.append({"role": meta.get("role", "user"), "content": r.content})
    except Exception as e:
        logger.warning("Conversation msg history failed: %s", e)

    if user_message.strip():
        await save_msg([{"role": "user", "content": user_message}])

    planner = _get_planner()

    from app.planner.planner import set_active_session
    set_active_session(
        session=None,
        business_id=business_id,
        emit_callback=state.get("emit_callback"),
        session_id=session_id,
    )

    response_msg = await planner.run(
        user_request=user_message,
        conversation_messages=conversation_history[-12:],
    )
    print('>>>>>>>>>>>>>>.check',response_msg )
    text = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)

    try:
        scope = f"/conversations/{conversation_scope_id}"
        memory = Memory(scopes=[scope], business_id=business_id, table_name="conversations")
        await memory.save(content=user_message, metadata={"role": "user", "session_id": session_id})
        await memory.save(content=text, metadata={"role": "assistant", "session_id": session_id})
    except Exception as e:
        logger.warning("Conversation history persist failed: %s", e)

    await save_msg([{"role": "assistant", "content": text}])

    response_payload = {"mode": "conversation", "text": text, "msg_type": "answer"}

    return {
        "response": response_payload,
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": text},
        ],
    }
