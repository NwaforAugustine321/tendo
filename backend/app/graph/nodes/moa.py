"""MOA (Tendo) — Master Orchestrator Agent node.

Call-stack architecture: MOA runs once per request. It either answers directly,
routes to a specialist via delegation tools, or requests its own DB tools.
When returning from a tool call (return_to == "moa"), it incorporates results.

Uses hierarchical_manager_agent translations for role/goal/backstory (like CrewAI).
Only tools: DelegateWorkTool + AskQuestionTool for specialist routing.
"""

import json
import logging

from app.agents.models import Agent, DomainAgentOutput
from app.lib.agent_executor import execute_task
from app.lib.agent_tools import AgentTools
from app.lib.i18n import _get_i18n
from app.models.state import GraphState

logger = logging.getLogger(__name__)

# Specialist agents available for delegation
_SPECIALIST_SPECS = [
    "domain/inventory",
    "domain/transactions",
    "onboarding",
]


def _get_moa_agent() -> Agent:
    """Create MOA agent from i18n translations (hierarchical_manager_agent)."""
    i18n = _get_i18n()
    return Agent(
        role=i18n.get("hierarchical_manager_agent.role"),
        goal=i18n.get("hierarchical_manager_agent.goal"),
        backstory=i18n.get("hierarchical_manager_agent.backstory"),
        expected_output=Agent.from_spec("moa").expected_output,
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

    from app.lib.field_formatter import format_user_input
    user_message = format_user_input(user_message)

    logger.info(f"MOA: history has {len(history)} messages, business_id={business_id}")

    # If returning from a tool call the MOA itself made
    if state.get("return_to") == "moa" and state.get("domain_result"):
        domain_result = state.get("domain_result")
        summary = domain_result.get("summary", "")
        logger.info(f"MOA: got tool results back — {summary[:100]}")

        response_data = {"mode": "conversation", "text": summary}
        return {
            "response": response_data,
            "output_mode": "conversation",
            "domain_result": None,
            "return_to": None,
            "workflow_owner": None,
            "current_agent": None,
            "messages": [
                {"role": "assistant", "content": summary},
            ],
        }

    # Load MOA agent from translations
    agent = _get_moa_agent()

    # Load specialist agents and create delegation tools
    specialists = _get_specialist_agents()
    moa_tools = AgentTools(agents=specialists).tools()

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
    )

    logger.info(f"MOA raw output: {raw[:200]}")

    # Check if delegation tool was called — detect __ROUTE__ signal
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

    # Check if delegation happened but route signal wasn't extracted
    # (the raw contains Action: delegate_ patterns — try to infer route)
    if "Action: delegate_" in raw or "delegate_work" in raw:
        inferred_target = _infer_route_from_delegation(raw)
        if inferred_target:
            logger.info(f"MOA: inferred delegation → routing to {inferred_target}")
            return {
                "routed_domain": inferred_target,
                "current_agent": "moa",
                "workflow_owner": inferred_target,
                "return_to": inferred_target,
                "tool_requests": None,
                "response": {"mode": "conversation", "text": ""},
                "output_mode": "conversation",
                "messages": [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": f"Routing to {inferred_target}"},
                ],
            }

    decision = _parse_decision(raw)

    if decision.get("_retry"):
        logger.warning("MOA: invalid JSON output, using raw as response")
        decision = {"response": raw, "workflow_status": "completed"}

    text = decision.get("response", raw)

    # Strip internal reasoning from the text (never expose Thought/Action/Observation)
    text = _strip_internal_reasoning(text)

    target = decision.get("target")
    fields = decision.get("fields")
    tool_requests = decision.get("tool_requests")

    logger.info(f"MOA decision: target={target}, has_fields={bool(fields)}, has_tool_requests={bool(tool_requests)}")

    new_messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": text},
    ]

    # Route to a specialist
    if target:
        return {
            "routed_domain": target,
            "current_agent": "moa",
            "workflow_owner": target,
            "return_to": target,
            "response": {"mode": "conversation", "text": text},
            "output_mode": "conversation",
            "messages": new_messages,
        }

    # MOA needs its own DB tools (not delegation — those are handled inline above)
    if tool_requests and isinstance(tool_requests, list):
        # Ensure tool_requests only contains serializable dicts
        clean_requests = [
            {"tool": tr.get("tool", ""), "arguments": tr.get("arguments", tr.get("params", {}))}
            for tr in tool_requests
            if isinstance(tr, dict)
        ]
        return {
            "tool_requests": clean_requests,
            "return_to": "moa",
            "workflow_owner": "moa",
            "current_agent": "moa",
            "response": {"mode": "conversation", "text": text},
            "output_mode": "conversation",
            "messages": new_messages,
        }

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


def _strip_internal_reasoning(text: str) -> str:
    """Remove internal agent reasoning markers from text shown to users."""
    if not text:
        return text

    # If text contains Thought:/Action:/Observation: patterns, extract only clean response
    if "Thought:" in text or "Action:" in text or "Observation:" in text:
        # Try to extract Final Answer content
        if "Final Answer:" in text:
            after = text.split("Final Answer:", 1)[1].strip()
            # If it's JSON, try to extract .response from it
            if after.startswith("{"):
                try:
                    data = json.loads(after)
                    return data.get("response", after)
                except (json.JSONDecodeError, ValueError):
                    pass
            return after

        # If no Final Answer, try extracting Observation (specialist response)
        if "Observation:" in text:
            parts = text.split("Observation:")
            last_obs = parts[-1].strip()
            # Clean up any trailing Thought/Action
            for marker in ["Thought:", "Action:", "Action Input:"]:
                idx = last_obs.find(marker)
                if idx != -1:
                    last_obs = last_obs[:idx].strip()
            if last_obs:
                return last_obs

        # Last resort: remove everything before "Final Answer" or return cleaned
        return ""

    return text


def _infer_route_from_delegation(raw: str) -> str | None:
    """Infer routing target from delegation tool usage in raw output."""
    raw_lower = raw.lower()

    if "business profile" in raw_lower or "onboarding" in raw_lower:
        return "onboarding"
    if "transaction" in raw_lower or "sale" in raw_lower or "payment" in raw_lower:
        return "transactions"
    if "inventory" in raw_lower or "product" in raw_lower or "stock" in raw_lower:
        return "inventory"

    return None


def _parse_decision(raw: str) -> dict:
    """Parse MOA JSON output."""
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if clean.startswith("{"):
            return json.loads(clean)
        start = clean.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(clean)):
                if clean[i] == "{":
                    depth += 1
                elif clean[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return json.loads(clean[start:i + 1])
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"_retry": True}


def _extract_route_signal(raw: str) -> str | None:
    """Extract routing target from __ROUTE__ signal in output.

    The delegation tool returns __ROUTE__:{role}|task:...|context:...
    The LLM may echo this or include it in its response.

    Returns:
        The domain name to route to, or None if no route signal found.
    """
    if "__ROUTE__:" not in raw:
        return None

    # Map agent roles to domain names
    role_to_domain = {
        "transactions": "transactions",
        "inventory": "inventory",
        "onboarding": "onboarding",
        "you_help_users_create,_complete,_and_update_their_business_profile.": "onboarding",
        "you_are_the_inventory_agent.": "inventory",
        "you_handle_all_transaction-related_requests.": "transactions",
    }

    try:
        # Find __ROUTE__:{role}
        idx = raw.index("__ROUTE__:")
        after = raw[idx + 10:]
        role_part = after.split("|")[0].strip()

        # Try direct match
        if role_part in role_to_domain:
            return role_to_domain[role_part]

        # Try partial match
        for key, domain in role_to_domain.items():
            if key in role_part or role_part in key:
                return domain

        # If role_part looks like a domain name already
        if role_part in ("transactions", "inventory", "onboarding"):
            return role_part

    except (ValueError, IndexError):
        pass

    return None
