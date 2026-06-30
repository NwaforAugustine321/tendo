"""Onboarding node — collects business profile info through structured conversation.

Call-stack architecture: onboarding owns its workflow. When onboarding completes,
it issues a tool_request to update the business profile via tool_planner.
"""

import json
import logging

from app.agents.models import Agent, DomainAgentOutput
from app.db.tools.onboarding_tools import ONBOARDING_TOOLS
from app.memory.knowledge import search_business_knowledge
from app.lib.agent_executor import execute_task
from app.lib.user_input_tool import ask_user_question
from app.memory.memory import Memory, get_memory
from app.models.state import GraphState
from app.lib.json_parser import parse_json_output

logger = logging.getLogger(__name__)

# Load agent once at module level
_onboarding_agent = Agent.from_spec("onboarding")


async def onboarding_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    history = state.get("messages", [])
    thinking_callback = state.get("thinking_callback")

    from app.lib.field_formatter import format_user_input
    pending_question = state.get("pending_question")
    user_message = format_user_input(user_message, pending_question=pending_question)

   
    agent = _onboarding_agent

    context = f"business_id: {business_id}\nthread_id: {thread_id}"
    memory = get_memory(f"/business/{business_id}")

    all_tools = ONBOARDING_TOOLS + [search_business_knowledge]
    raw = await execute_task(
        agent=agent,
        description=user_message,
        tools=all_tools,
        expected_output=agent.expected_output,
        chat_history=history[-12:],
        context=context,
        output_pydantic=DomainAgentOutput,
        memory=memory,
        use_system_prompt=True,
        
        thinking_callback=thinking_callback,
    )

    logger.info(f"Onboarding raw output: {raw[:200]}")

    parsed = parse_json_output(raw)
    text = parsed.get("response", raw)
    fields = parsed.get("fields")
    workflow_status = parsed.get("workflow_status", "completed")

    response_data = {"mode": "conversation", "text": text, "workflow_status": workflow_status}
    if fields:
        response_data["input"] = {"fields": fields}

    extracted = parsed.get("extracted")
    if extracted:
        response_data["extracted"] = extracted

    # Check if onboarding is complete
    is_complete = parsed.get("status") == "complete"
    business_data = {}

    if is_complete:
        business_data = {
            "business_name": parsed.get("business_name", ""),
            "business_type": parsed.get("business_type", ""),
            "description": parsed.get("description", ""),
            "phone_number": parsed.get("phone_number", ""),
            "location": parsed.get("location", ""),
            "logo_url": parsed.get("logo", ""),
            "metadata": parsed.get("metadata", {}),
            "onboarding_complete": True,
        }
        response_data["business_data"] = business_data

    result = {
        "response": response_data,
        "output_mode": "conversation",
        "workflow_owner": "onboarding",
        "current_agent": "onboarding",
        "pending_question": text if workflow_status == "waiting_for_user" else None,
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
        ],
    }

    return result


