import asyncio
import logging
from typing import Any
from app.db.tools.sessions import insert_session
from app.db.tools.messages import save_messages
from app.memory.memory import Memory
from app.planner import Planner


logger = logging.getLogger(__name__)

global _planner


async def moa_node(state: dict) -> dict:

    user_message = state.get("text", "")
    business_id = state.get("business_id")
    session_id = state.get("session_id")
    record_id = state.get("record_id", "")
    user_id = state.get("user_id")
    thread_id = state.get('thread_id', '')

    session = {
        "vc_session": None,
        "business_id": business_id,
        "session_id": session_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "record_id": record_id,
    }

    planner = Planner(session_context=session)

    response = await planner.run(
        user_message=user_message
    )

    response_payload = {"mode": "conversation",
                        "text":  response, "msg_type": "answer"}

    return {
        "response": response_payload,
        "type": "message"
    }
