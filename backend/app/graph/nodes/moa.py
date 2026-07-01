"""MOA (Tendo) — Master Orchestrator Agent node.
"""

import json
import logging

from app.agents.models import Agent, DomainAgentOutput
from app.lib.agent_executor import execute_task
from app.lib.agent_tools import AgentTools
from app.memory.knowledge import search_business_knowledge
from app.lib.i18n import _get_i18n
from app.models.state import GraphState
from app.lib.json_parser import parse_json_output
from app.db.tools.profile_tools import get_business_profile

logger = logging.getLogger(__name__)

# Specialist agents available for delegation
_SPECIALIST_SPECS = [
    "inventory",
    "transactions",
    "onboarding",
]


def _get_moa_agent() -> Agent:
    """Create MOA agent from i18n translations (hierarchical_manager_agent)."""
    i18n = _get_i18n()
    return Agent(
        role=Agent.from_spec("moa").role,  #i18n.get("hierarchical_manager_agent.role"),
        goal=Agent.from_spec("moa").goal,  #i18n.get("hierarchical_manager_agent.goal"),
        backstory=Agent.from_spec("moa").backstory,  #i18n.get("hierarchical_manager_agent.backstory"),
        skill=Agent.from_spec("moa").skill,
    )


def _get_specialist_agents() -> list[Agent]:
    """Load specialist agents for delegation tools."""
    agents = []
    for spec in _SPECIALIST_SPECS:
        try:
            agents.append(Agent.from_spec(spec))
        except FileNotFoundError:
            logger.warning(f"Specialist spec not found: {spec}")
    return agents


async def moa_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    history = state.get("messages", [])
    thinking_callback = state.get("thinking_callback")

    from app.lib.field_formatter import format_user_input
    from app.db.tools.messages import fetch_messages, save_messages, get_pending_question

    # Fetch persisted messages from DB (reliable across invocations)
    thread_id_for_db = thread_id or ""

    # Save user message immediately so pending_question detection works correctly
    if business_id and thread_id_for_db and event.get("text", "").strip():
        await save_messages(business_id, thread_id_for_db, [
            {"role": "user", "content": event.get("text", "")},
        ])

    db_messages = await fetch_messages(business_id, thread_id_for_db, limit=10) if business_id and thread_id_for_db else []

    # Use DB messages if available, fallback to state messages
    effective_history = db_messages if db_messages else history[-12:]

    # Derive pending_question from last assistant message in persisted history
    pending_question = get_pending_question(db_messages)
    user_message = format_user_input(user_message, pending_question=pending_question)

    logger.info(f"MOA: history has {len(effective_history)} messages, business_id={business_id}, pending_question={bool(pending_question)}, formatted_msg={user_message[:100]}")

    agent = _get_moa_agent()

    
  
    moa_tools = AgentTools(agents=_SPECIALIST_SPECS).tools() + [search_business_knowledge, get_business_profile]


    context = f"business_id: {business_id}\nthread_id: {thread_id}"

    # Execute using our lib pipeline
    raw = await execute_task(
        agent=agent,
        description=user_message,
        tools=moa_tools,
        expected_output=agent.expected_output,
        chat_history=effective_history,
        context=context,
        output_pydantic=DomainAgentOutput,
        use_system_prompt=True,
        thinking_callback=thinking_callback,
    )

    logger.info(f"MOA raw output: {raw}")

    # # Check if delegation tool was called — detect __ROUTE__ signal
    route_target = _extract_route_signal(raw)
    if route_target:
        logger.info(f"MOA: delegation detected → routing to {route_target}")
        return {
            "routed_domain": route_target,
            "current_agent": "moa",
            "workflow_owner": route_target,
            "return_to": route_target,
            "tool_requests": None,
            "response": {"mode": "conversation", "text": ""},
            "output_mode": "conversation",
            "messages": [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": f"Routing to {route_target}"},
            ],
        }

    
    try:
        decision = parse_json_output(raw)
    except (json.JSONDecodeError, IndexError, ValueError):
         logger.warning("MOA: invalid JSON output, using raw as response")
         decision = {"response": raw, "workflow_status": "completed"}

    text = decision.get("response", raw)



    fields = decision.get("fields")
    tool_requests = decision.get("tool_requests")

    new_messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": text},
    ]

    # Direct answer — no routing needed
    response_data = {"mode": "conversation", "text": text}
    if fields:
        response_data["input"] = {"fields": fields}

    # Set pending_question if MOA is waiting for user input
    is_waiting = decision.get("workflow_status") == "waiting_for_user"

    result = {
        "routed_domain": None,
        "current_agent": None,
        "workflow_owner": None,
        "return_to": None,
        "pending_question": text if is_waiting else None,
        "response": response_data,
        "output_mode": "conversation",
        "messages": new_messages,
    }

    # Persist assistant response to DB (user message already saved at start)
    if business_id and thread_id_for_db:
        await save_messages(business_id, thread_id_for_db, [
            {"role": "assistant", "content": raw},
        ])

    return result


def _extract_route_signal(raw: str) -> str | None:
    """Extract routing target from __ROUTE__ signal in output.

    Returns:
        The domain name to route to, or None if no route signal found.
    """
    if "__ROUTE__:" not in raw:
        return None

    try:
        idx = raw.index("__ROUTE__:")
        after = raw[idx + 10:]
        role_part = after.split("|")[0].strip().lower()

        # Exact domain name
        if role_part in ("transactions", "inventory", "onboarding"):
            return role_part

    except (ValueError, IndexError):
        pass

    return None


def _build_direct_response(user_message: str, text: str) -> dict:
    """Build a direct response dict (no routing, no delegation)."""
    return {
        "routed_domain": None,
        "current_agent": None,
        "workflow_owner": None,
        "return_to": None,
        "response": {"mode": "conversation", "text": text},
        "output_mode": "conversation",
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": text},
        ],
    }
