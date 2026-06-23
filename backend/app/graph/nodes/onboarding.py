"""Onboarding node — collects business profile info through structured conversation.

Call-stack architecture: onboarding owns its workflow. When onboarding completes,
it issues a tool_request to update the business profile via tool_planner.
"""

import json
import logging

from app.agents.models import Agent, DomainAgentOutput
from app.db.tools.onboarding_tools import ONBOARDING_TOOLS
from app.lib.agent_executor import execute_task
from app.lib.user_input_tool import ask_user_question
from app.memory.memory import Memory, get_memory
from app.models.state import GraphState

logger = logging.getLogger(__name__)

# Load agent once at module level
_onboarding_agent = Agent.from_spec("onboarding")


async def onboarding_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    history = state.get("messages", [])

    from app.lib.field_formatter import format_user_input
    user_message = format_user_input(user_message)

    # Return from tool_planner (db_translator just ran)
    domain_result = state.get("domain_result")
    if domain_result and state.get("return_to") == "onboarding":
        summary = domain_result.get("summary", "")
        logger.info(f"Onboarding: got tool results back — {summary[:100]}")

        response_data = {"mode": "conversation", "text": summary}
        return {
            "response": response_data,
            "output_mode": "conversation",
            "domain_result": None,
            "return_to": None,
            "workflow_owner": None,
            "current_agent": None,
            "tool_requests": None,
            "messages": [
                {"role": "assistant", "content": summary},
            ],
        }

    # Use module-level agent
    agent = _onboarding_agent

    # Context
    context = f"business_id: {business_id}\nthread_id: {thread_id}"

    # Memory for this business (cached, not recreated per request)
    memory = get_memory(f"/business/{business_id}")

    # Execute using our lib pipeline
    raw = await execute_task(
        agent=agent,
        description=user_message,
        tools=ONBOARDING_TOOLS + [ask_user_question],
        expected_output=agent.expected_output,
        chat_history=history[-12:],
        context=context,
        output_pydantic=DomainAgentOutput,
        memory=memory,
        use_system_prompt=True,
        max_iter=3,
    )

    logger.info(f"Onboarding raw output: {raw[:200]}")

    # Parse response
    parsed = _parse_response(raw)
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
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
        ],
    }

    # When onboarding completes, save the profile via tool_planner
    if is_complete:
        logo = business_data["logo_url"]
        result["tool_requests"] = [{
            "tool": "update_business_profile",
            "arguments": {
                "business_id": business_id,
                "name": business_data["business_name"],
                "category": business_data["business_type"],
                "description": business_data["description"],
                "phone": business_data["phone_number"],
                "location": business_data["location"],
                "logo_url": logo if isinstance(logo, str) and logo.startswith("http") else "",
                "onboarding_completed": True,
                "metadata": business_data["metadata"],
            }
        }]
        result["return_to"] = "onboarding"
        result["workflow_owner"] = "onboarding"

    return result


def _parse_response(raw: str) -> dict:
    """Parse onboarding agent JSON output. Also handles __WAITING__ tool signal."""
    # Handle __WAITING__ signal from ask_user_question tool
    if "__WAITING__|" in raw:
        try:
            json_part = raw.split("__WAITING__|", 1)[1]
            return json.loads(json_part)
        except (json.JSONDecodeError, IndexError):
            return {"response": raw.strip(), "workflow_status": "waiting_for_user"}

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        start = clean.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(clean)):
                if clean[i] == "{":
                    depth += 1
                elif clean[i] == "}":
                    depth -= 1
                    if depth == 0:
                        parsed = json.loads(clean[start: i + 1])
                        if "response" in parsed:
                            return parsed
                        break
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"response": raw.strip(), "workflow_status": "completed"}
