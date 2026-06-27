"""MOA (Tendo) — Master Orchestrator Agent node.
"""

import json
import logging

from app.agents.models import Agent, DomainAgentOutput
from app.lib.agent_executor import execute_task
from app.lib.agent_tools import AgentTools
from app.db.tools.knowledge import search_business_knowledge
from app.lib.i18n import _get_i18n
from app.models.state import GraphState
from app.lib.json_parser import parse_json_output

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
        role=i18n.get("hierarchical_manager_agent.role"),
        goal=i18n.get("hierarchical_manager_agent.goal"),
        backstory=i18n.get("hierarchical_manager_agent.backstory"),
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
    user_message = format_user_input(user_message)

    logger.info(f"MOA: history has {len(history)} messages, business_id={business_id}")

    # Load MOA agent from translations
    agent = _get_moa_agent()

    # Load specialist agents and create delegation tools
    
    moa_tools = AgentTools(agents=_SPECIALIST_SPECS).tools() 

    # Context (business-specific only — tools are injected via prompts.py)
    context = f"business_id: {business_id}\nthread_id: {thread_id}"

    # Execute using our lib pipeline
    raw = await execute_task(
        agent=agent,
        description=user_message,
        tools=moa_tools,
        expected_output=agent.expected_output,
        chat_history=history[-12:],
        context=context,
        output_pydantic=DomainAgentOutput,
        use_system_prompt=True,
        max_iter=5,
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

    result = {
        "routed_domain": None,
        "current_agent": None,
        "workflow_owner": None,
        "return_to": None,
        "response": response_data,
        "output_mode": "conversation",
        "messages": new_messages,
    }

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
