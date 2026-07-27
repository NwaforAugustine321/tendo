"""MOA Orchestrator — Plan → Execute (parallel/sequential) → Merge → Compose response."""

import asyncio
import logging
from typing import Any

from app.agents.domains import OnboardingAgent, TransactionsAgent, InventoryAgent, KnowledgeAgent
from app.contexts.models import SharedContext
from app.execution.models import AgentExecution, DomainResult, ExecutionMetrics
from app.merge.merger import Merger, MergedResult
from app.planner import ExecutionOrder, ExecutionPlan, Planner, PlanningError
from app.planner.models import AgentAssignment
from app.response.composer import ResponseComposer
from app.runtime import AgentRuntime, ToolBinder
from app.skills.manager import SkillManager

logger = logging.getLogger(__name__)

MAX_CONCURRENT_AGENTS = 10
ORCHESTRATION_TIMEOUT_SECONDS = 120

_AGENT_REGISTRY: dict[str, Any] = {
    "onboarding": OnboardingAgent,
    "transactions": TransactionsAgent,
    "inventory": InventoryAgent,
    "knowledge": KnowledgeAgent,
}


def _get_domain_agent(agent_id: str) -> Any:
    agent_class = _AGENT_REGISTRY.get(agent_id)
    if agent_class is None:
        # Try stripping common suffixes the LLM might add
        clean_id = agent_id.replace("_agent", "").replace("-agent", "")
        agent_class = _AGENT_REGISTRY.get(clean_id)
    if agent_class is None:
        raise ValueError(f"Unknown agent_id: {agent_id}")
    return agent_class()


async def moa_orchestrator(
    user_request: str,
    business_id: str,
    thinking_callback: Any | None = None,
    uploaded_files: list[str] | None = None,
    conversation_messages: list[dict] | None = None,
    scope: str = "knowledge",
    record_id: str = "",
    scopes: list[str] | None = None,
) -> dict:
    """Full orchestration: Plan → Execute → Merge → Compose."""
    from app.llm.client import get_client

    llm = get_client()
    planner = Planner(llm=llm)

    try:
        plan = await planner.plan(
            user_request=user_request,
            business_id=business_id,
            uploaded_files=uploaded_files,
            conversation_messages=conversation_messages,
            scope=scope,
            record_id=record_id,
        )
    except PlanningError as e:
        logger.error("Planning failed: %s — falling back to direct response", e)
        response_text = await _direct_response(llm, user_request, conversation_messages)
        return {"response": {"mode": "conversation", "text": response_text}}

    if plan.unresolvable:
        response_text = await _direct_response(llm, user_request, conversation_messages)
        return {"response": {"mode": "conversation", "text": response_text}}

    executions = await _execute_plan(plan, thinking_callback, business_id, scopes)

    merger = Merger()
    merged = await merger.merge(executions)

    skill_manager = SkillManager(business_id=business_id)
    composer = ResponseComposer(skill_manager=skill_manager)

    response = await composer.compose(merged, streaming_callback=thinking_callback)
    return response


async def _direct_response(llm: Any, user_request: str, conversation_messages: list[dict] | None = None) -> str:
    """Handle general conversation using the MOA agent's system prompt via AgentRuntime."""
    from app.agents.models import Agent

    moa_agent = Agent.from_spec("moa")
    system = moa_agent.backstory or moa_agent.goal or ""
    messages = [{"role": "system", "content": system}]
    # Include actual conversation messages
    if conversation_messages:
        for msg in conversation_messages:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_request})

    runtime = AgentRuntime(llm=llm, tool_binder=ToolBinder(), max_iter=5)
    runtime._messages = messages
    runtime._iterations = 0
    runtime._tool_call_history = set()
    return await runtime._invoke_loop()


async def _execute_plan(plan: ExecutionPlan, thinking_callback: Any | None, business_id: str = "", scopes: list[str] | None = None) -> list[AgentExecution]:
    if plan.execution_order == ExecutionOrder.PARALLEL:
        return await _execute_parallel(plan, thinking_callback, business_id, scopes)
    return await _execute_sequential(plan, thinking_callback, business_id, scopes)


async def _execute_parallel(plan: ExecutionPlan, thinking_callback: Any | None, business_id: str = "", scopes: list[str] | None = None) -> list[AgentExecution]:
    from app.llm.client import get_client

    biz_id = business_id or plan.shared_context.business_id

    async def run_agent(assignment: AgentAssignment) -> AgentExecution:
        try:
            from app.runtime.tool_registry import build_tool_registry

            domain_agent = _get_domain_agent(assignment.agent_id)
            tools = domain_agent.get_tools(business_id=biz_id, scopes=scopes)
            registry = build_tool_registry(tools=tools)

            llm = get_client()
            tool_binder = ToolBinder(tool_registry=registry)
            runtime = AgentRuntime(
                llm=llm,
                tool_binder=tool_binder,
                thinking_callback=thinking_callback,
            )
            return await runtime.execute(
                execution_context=assignment.execution_context,
                shared_context=plan.shared_context,
                domain_agent=domain_agent,
            )
        except Exception as e:
            logger.error("Agent '%s' failed: %s", assignment.agent_id, e)
            return AgentExecution(
                agent_id=assignment.agent_id,
                execution_context=assignment.execution_context,
                result=DomainResult(status="failure"),
                metrics=ExecutionMetrics(),
                error=str(e),
            )

    try:
        async with asyncio.timeout(ORCHESTRATION_TIMEOUT_SECONDS):
            tasks = [run_agent(a) for a in plan.participating_agents[:MAX_CONCURRENT_AGENTS]]
            return await asyncio.gather(*tasks)
    except asyncio.TimeoutError:
        logger.error("Orchestration timeout after %ds", ORCHESTRATION_TIMEOUT_SECONDS)
        return [
            AgentExecution(
                agent_id=a.agent_id,
                execution_context=a.execution_context,
                result=DomainResult(status="failure"),
                metrics=ExecutionMetrics(),
                error="Orchestration timeout",
            )
            for a in plan.participating_agents
        ]


async def _execute_sequential(plan: ExecutionPlan, thinking_callback: Any | None, business_id: str = "", scopes: list[str] | None = None) -> list[AgentExecution]:
    from app.llm.client import get_client

    biz_id = business_id or plan.shared_context.business_id
    executions: list[AgentExecution] = []

    try:
        async with asyncio.timeout(ORCHESTRATION_TIMEOUT_SECONDS):
            for assignment in plan.participating_agents:
                try:
                    from app.runtime.tool_registry import build_tool_registry

                    domain_agent = _get_domain_agent(assignment.agent_id)
                    tools = domain_agent.get_tools(business_id=biz_id, scopes=scopes)
                    registry = build_tool_registry(tools=tools)

                    llm = get_client()
                    tool_binder = ToolBinder(tool_registry=registry)
                    runtime = AgentRuntime(
                        llm=llm,
                        tool_binder=tool_binder,
                        thinking_callback=thinking_callback,
                    )
                    result = await runtime.execute(
                        execution_context=assignment.execution_context,
                        shared_context=plan.shared_context,
                        domain_agent=domain_agent,
                    )
                    executions.append(result)
                except Exception as e:
                    logger.error("Agent '%s' failed: %s", assignment.agent_id, e)
                    executions.append(AgentExecution(
                        agent_id=assignment.agent_id,
                        execution_context=assignment.execution_context,
                        result=DomainResult(status="failure"),
                        metrics=ExecutionMetrics(),
                        error=str(e),
                    ))
    except asyncio.TimeoutError:
        logger.error("Orchestration timeout after %ds", ORCHESTRATION_TIMEOUT_SECONDS)
        for a in plan.participating_agents[len(executions):]:
            executions.append(AgentExecution(
                agent_id=a.agent_id,
                execution_context=a.execution_context,
                result=DomainResult(status="failure"),
                metrics=ExecutionMetrics(),
                error="Orchestration timeout",
            ))

    return executions



async def moa_orchestrator_node(state: "GraphState") -> dict:
    """LangGraph node that bridges state to the MOA Orchestrator."""
    from app.db.tools.messages import fetch_messages, save_messages
    from app.models.state import GraphState

    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    thinking_callback = state.get("thinking_callback")
    history = state.get("messages", [])

    thread_id_for_db = thread_id or ""

    if business_id and thread_id_for_db and user_message.strip():
        await save_messages(business_id, thread_id_for_db, [
            {"role": "user", "content": user_message},
        ])

    db_messages = await fetch_messages(business_id, thread_id_for_db, limit=10) if business_id and thread_id_for_db else []
    effective_history = db_messages if db_messages else history[-12:]

    conversation_messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in effective_history[-8:]]

    result = await moa_orchestrator(
        user_request=user_message,
        business_id=business_id,
        thinking_callback=thinking_callback,
        conversation_messages=conversation_messages,
    )

    response_text = result.get("response", "")
    if isinstance(response_text, dict):
        text = response_text.get("text", response_text.get("response", ""))
    else:
        text = str(response_text)

    if business_id and thread_id_for_db:
        await save_messages(business_id, thread_id_for_db, [
            {"role": "assistant", "content": text},
        ])

    return {
        "response": {"mode": "conversation", "text": text},
        "output_mode": "conversation",
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": text},
        ],
    }
