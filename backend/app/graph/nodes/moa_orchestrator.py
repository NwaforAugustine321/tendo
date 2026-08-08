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
    emit_event = state.get("emit_event")
    user_id = state.get("user_id")
    thread_id = state.get('thread_id','')
    emit_event = state.get("emit_event", None)
    
    session = {
       "vc_session": None,
       "business_id": business_id,
       "session_id": session_id,
       "user_id": user_id,
       "thread_id": thread_id,
       "record_id": record_id,
       "emit_event": emit_event
    }

    planner = Planner(session=session)

    # async def save_msg(messages):
    #     await save_messages(business_id, session_id, messages, record_id=record_id or None)

    # memory = Memory(
    #         scopes=[f"/conversations/{session_id}"],
    #         business_id=business_id,
    #         table_name="conversations",
    # )
    # conversation_history = []

    # try:
    #     recent = await memory.fetch(limit=10)
    #     for r in recent:
    #         meta = r.metadata or {}
    #         conversation_history.append({"role": meta.get("role", "user"), "content": r.content})
    # except Exception as e:
    #     logger.warning("Conversation msg history failed: %s", e)

    # if user_message.strip():
    #     await save_msg([{"role": "user", "content": user_message}])

    response = await planner.run(
        user_message=user_message
    )
  
    # text = response_msg.content or ""

    # try:
    #     await memory.save(content=user_message, metadata={"role": "user", "session_id": session_id})
    #     await memory.save(content=text, metadata={"role": "assistant", "session_id": session_id})
    # except Exception as e:
    #     logger.warning("Conversation history persist failed: %s", e)

    # await save_msg([{"role": "assistant", "content": text}])

    response_payload = {"mode": "conversation", "text":  response, "msg_type": "answer"}

    return {
        "response": response_payload,
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response},
        ],
    }
