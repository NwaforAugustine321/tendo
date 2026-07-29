"""MOA Orchestrator graph node — handles message fetching, scope/session, orchestration, and persistence."""

import asyncio
import logging
from typing import Any

from app.agents.specs.domain import  TransactionsAgent, InventoryAgent, KnowledgeAgent
from app.agents.specs.moa.agent import MoaAgent
from app.execution.models import Execution, Result, ExecutionMetrics
from app.merge.merger import Merger, MergedResult
from app.planner import ExecutionOrder, ExecutionPlan, Planner, PlanningError
from app.planner.models import AgentAssignment
from app.response.composer import ResponseComposer
from app.runtime import AgentRuntime, ToolBinder
from app.skills.manager import SkillManager
from app.llm.client import get_client

llm = get_client()

logger = logging.getLogger(__name__)

MAX_CONCURRENT_AGENTS = 10
ORCHESTRATION_TIMEOUT_SECONDS = 120

moa_agent = MoaAgent()

_AGENT_REGISTRY: dict[str, Any] = {
    "transaction_agent": TransactionsAgent(),
    "inventory_agent": InventoryAgent(),
    "general_information_agent": KnowledgeAgent(),
}


def _get_agent(agent_id: str) -> Any:
    agent = _AGENT_REGISTRY.get(agent_id)

    if agent is None:
        raise ValueError(f"Unknown agent_id: {agent_id}")

    return agent



async def moa_orchestrator(
    user_request: str,
    business_id: str,
    thinking_callback: Any | None = None,
    conversation_messages: list[dict] | None = None,
    record_id: str = "",
    scopes: list[str] | None = None,
) -> dict:


    planner = Planner()

    try:
        plan = await planner.plan(
            user_request=user_request,
            conversation_messages=conversation_messages,
        )
        print(plan)
       
    except PlanningError as e:
        logger.error("Planning failed: %s — falling back to direct response", e)
        response_text = await _direct_response(llm, user_request, conversation_messages)
        return {"response": {"mode": "conversation", "text": response_text}}

    if plan.unresolvable:
        return {"response": {"mode": "conversation", "text": plan.unresolvable_reason}}

    executions = await _execute_plan(user_request,plan, thinking_callback, business_id, scopes)

    merger = Merger()
    merged = await merger.merge(executions)

    skill_manager = SkillManager(business_id=business_id)
    composer = ResponseComposer(skill_manager=skill_manager)

    response = await composer.compose(merged, streaming_callback=thinking_callback)
    return response
    return {}


async def _direct_response(llm: Any, user_request: str, conversation_messages: list[dict] | None = None) -> str:   
    result = await moa_agent.execute_agent(
                user_request,
                chat_history=conversation_messages
            )
    if hasattr(result, 'result'):
        return result.result.response
    return str(result)


async def _execute_plan(user_request: str, plan: ExecutionPlan, thinking_callback: Any | None, business_id: str = "", scopes: list[str] | None = None) -> list[Execution]:
    if plan.execution_order == ExecutionOrder.PARALLEL:
        return await _execute_parallel(user_request, plan, thinking_callback, business_id, scopes)
    return await _execute_sequential(user_request, plan, thinking_callback, business_id, scopes)


async def _execute_parallel(user_request:str, plan: ExecutionPlan, thinking_callback: Any | None, business_id: str = "", scopes: list[str] | None = None) -> list[Execution]:
    from app.llm.client import get_client

    _business_id = business_id or plan.shared_context.business_id

    async def run_agent(assignment: AgentAssignment) -> Execution:
        try:
       

            agent = _get_agent(assignment.agent_id)
            agent.bind_tools(business_id, scopes=scopes)
            
            return await agent.execute_agent(
                #assignment.execution_context,
                user_request,
                chat_history=plan.shared_context.conversation_messages
            )

        except Exception as e:
            logger.error("Agent '%s' failed: %s", assignment.agent_id, e)
            return Execution(
                agent_id=assignment.agent_id,
                result=Result(status="failure"),
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
            Execution(
                agent_id=a.agent_id,
                result=Result(status="failure"),
                metrics=ExecutionMetrics(),
                error="Orchestration timeout",
            )
            for a in plan.participating_agents
        ]


async def _execute_sequential(user_request:str, plan: ExecutionPlan, thinking_callback: Any | None, business_id: str = "", scopes: list[str] | None = None) -> list[Execution]:
    from app.llm.client import get_client

    biz_id = business_id or plan.shared_context.business_id
    executions: list[Execution] = []

    try:
        async with asyncio.timeout(ORCHESTRATION_TIMEOUT_SECONDS):
            for assignment in plan.participating_agents:
                try:
                    
                    agent = _get_agent(assignment.agent_id)
                    agent.bind_tools(business_id, scopes=scopes)
            
                    result = await agent.execute_agent(
                    #    assignment.execution_context,
                        user_request,
                       chat_history=plan.shared_context.conversation_messages
                    )

                    executions.append(result)
                except Exception as e:
                    logger.error("Agent '%s' failed: %s", assignment.agent_id, e)
                    executions.append(Execution(
                        agent_id=assignment.agent_id,
                        result=Result(status="failure"),
                        metrics=ExecutionMetrics(),
                        error=str(e),
                    ))
    except asyncio.TimeoutError:
        logger.error("Orchestration timeout after %ds", ORCHESTRATION_TIMEOUT_SECONDS)
        for a in plan.participating_agents[len(executions):]:
            executions.append(Execution(
                agent_id=a.agent_id,
                result=Result(status="failure"),
                metrics=ExecutionMetrics(),
                error="Orchestration timeout",
            ))

    return executions


async def moa_orchestrator_node(state: "GraphState") -> dict:


    from app.db.tools.messages import  save_messages
    from app.memory.memory import Memory
    from app.models.state import GraphState

    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    session_id = state.get("session_id") or event.get("session_id", "")
    emit_callback = state.get("emit_callback")
    record_id = event.get("record_id", "")
    scopes = event.get("scopes")


    thinking_callback = None
    if emit_callback:
        async def thinking_callback(msg):
            if isinstance(msg, dict):
                thinking_text = msg.get("data", str(msg))
            else:
                thinking_text = str(msg)
            await emit_callback("message", {"type": "thinking", "data": thinking_text})
    elif state.get("thinking_callback"):
        # Legacy path: voice.py passes thinking_callback directly in state
        thinking_callback = state.get("thinking_callback")
    
    async def save_msg_to_long_term_mem(messages):
        if not session_id:
            return
        await save_messages(business_id, session_id, messages)

    conversation_scope_id = session_id

    async def save_msg_to_short_mem():
        try:
          scope = f"/conversations/{conversation_scope_id}"
          memory = Memory(scopes=[scope], business_id=business_id, table_name="conversations")
          await memory.save(content=user_message, metadata={"role": "user", "session_id": session_id})
          assistant_meta = {"role": "assistant", "session_id": session_id}
          if is_waiting:
            assistant_meta["waiting_for_user"] = True
            if questions:
                assistant_meta["questions"] = questions
          await memory.save(content=text, metadata=assistant_meta)
        except Exception as e:
            logger.warning("Conversation history persist failed: %s", e)

    async def fetch_short_msg_mem(limit:int = 10):
        messages: list[dict] = []
        try:
            memory = Memory(
                scopes=[f"/conversations/{conversation_scope_id}"],
                business_id=business_id,
                table_name="conversations",
            )
            recent = await memory.fetch(limit=limit)

            if recent:
                for r in recent:
                    meta = r.metadata or {}
                    messages.append({"role": meta.get("role", "user"), "content": r.content})
            return messages
        except Exception as e:
            logger.warning("Conversation msg history failed: %s", e)

    if scopes is None and record_id:
        scopes = [f"/{business_id}/record/{record_id}", f"/business/{business_id}"]


    conversation_history, _ = await asyncio.gather(
       asyncio.create_task(fetch_short_msg_mem(limit=10)),  
       asyncio.create_task(
         save_msg_to_long_term_mem([{"role": "user", "content": user_message}])
         if user_message.strip() else asyncio.sleep(0)), 
       return_exceptions=True
    )

    result = await moa_orchestrator(
        user_request=user_message,
        business_id=business_id,
        thinking_callback=thinking_callback,
        conversation_messages=conversation_history[-12:],
        scopes=scopes,
    )

    response = result.get("response", "")

    if isinstance(response, dict):
        text = response.get("text", response.get("response", ""))
    else:
        text = str(response)

    is_waiting = False
    questions = None
    try:
        from app.lib.json_parser import parse_json_output
        parsed = parse_json_output(text) if text.strip().startswith("{") else None
        if parsed and isinstance(parsed, dict):
            if parsed.get("workflow_status") == "waiting_for_user" or parsed.get("fields"):
                is_waiting = True
                questions = parsed.get("fields", [])
                text = parsed.get("response", text)
    except Exception:
        pass

    await save_msg_to_short_mem()
    await save_msg_to_long_term_mem([
            {"role": "assistant", "content": text},
    ])

    response_payload = {"mode": "conversation", "text": text}
    if is_waiting and questions:
        response_payload["msg_type"] = "question"
        response_payload["questions"] = questions
    else:
        response_payload["msg_type"] = "answer"

    return {
        "response": response_payload,
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": text},
        ],
    }
