

import asyncio
import logging
from typing import Any
from app.db.tools.messages import  save_messages
from app.memory.memory import Memory
from app.models.state import GraphState
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
from typing import Callable

llm = get_client()

logger = logging.getLogger(__name__)

MAX_CONCURRENT_AGENTS = 10

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
    conversation_messages: list[dict] | None = None,
    record_id: str = "",
    scopes: list[str] | None = None,
    emit_callback:Callable | None = None
) -> dict:


    planner = Planner()

    try:
        plan = await planner.plan(
            user_request=user_request,
            conversation_messages=conversation_messages,
        )
     
       
    except PlanningError as e:
        logger.error("Planning failed: %s — falling back to direct response", e)
        response_text = await _direct_response(llm, user_request, conversation_messages)
        return {"response": {"mode": "conversation", "text": response_text}}

    if plan.unresolvable:
        if plan.unresolvable_reason and not _is_meta_response(plan.unresolvable_reason):
            return {"response": {"mode": "conversation", "text": plan.unresolvable_reason}}
        response_text = await _direct_response(llm, user_request, conversation_messages)
        return {"response": {"mode": "conversation", "text": response_text}}

    executions = await _execute_plan(user_request,plan, business_id, scopes)

    merger = Merger()
    merged = await merger.merge(executions)

    skill_manager = SkillManager(business_id=business_id)
    composer = ResponseComposer(skill_manager=skill_manager)

    response = await composer.compose(merged)
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


def _is_meta_response(text: str) -> bool:
    meta_patterns = [
        "appears to be a normal conversational",
        "no specific knowledge",
        "no sub-crew plan",
        "no sub‑crew plan",
        "no agents needed",
        "does not require",
    ]
    lower = text.lower()
    return any(p in lower for p in meta_patterns)


async def _execute_plan(user_request: str, plan: ExecutionPlan, business_id: str = "", scopes: list[str] | None = None) -> list[Execution]:
    if plan.execution_order == ExecutionOrder.PARALLEL:
        return await _execute_parallel(user_request, plan,  business_id, scopes)
    return await _execute_sequential(user_request, plan,  business_id, scopes)


async def _execute_parallel(user_request:str, plan: ExecutionPlan,  business_id: str = "", scopes: list[str] | None = None) -> list[Execution]:
    from app.llm.client import get_client

    _business_id = business_id or plan.shared_context.business_id

    async def run_agent(assignment: AgentAssignment) -> Execution:
        try:
       

            agent = _get_agent(assignment.agent_id)
            agent.bind_tools(business_id, scopes=scopes)
            
            return await agent.execute_agent(
                assignment.execution_context,
                # user_request,
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

    tasks = [run_agent(a) for a in plan.participating_agents[:MAX_CONCURRENT_AGENTS]]
    return await asyncio.gather(*tasks)


async def _execute_sequential(user_request:str, plan: ExecutionPlan, business_id: str = "", scopes: list[str] | None = None) -> list[Execution]:
    from app.llm.client import get_client

    biz_id = business_id or plan.shared_context.business_id
    executions: list[Execution] = []

    for assignment in plan.participating_agents:
        try:
            
            agent = _get_agent(assignment.agent_id)
            agent.bind_tools(business_id, scopes=scopes)
    
            result = await agent.execute_agent(
                assignment.execution_context,
                # user_request,
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

    return executions


async def moa_orchestrator_node(state: "GraphState") -> dict:

    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    session_id = state.get("session_id") or event.get("session_id", "")
    record_id = event.get("record_id", "")
    scopes = event.get("scopes")
    emit_callback = state.get("emit_callback")
    user_id = state.get("user_id") or "anonymous"

    # Auto-create session if missing (e.g. voice path without a pre-created session)
    if not session_id and business_id:
        from app.db.tools.sessions import insert_session
        try:
            title = user_message[:50] if user_message else "Voice Session"
            new_session = await insert_session(business_id, user_id, title=title)
            session_id = new_session.get("id", "")
            print(f"[MOA_NODE] Auto-created session: {session_id}")
        except Exception as e:
            print(f"[MOA_NODE] Failed to auto-create session: {e}")

    print(f"[MOA_NODE] === START === user_message={user_message[:80] if user_message else ''}")
    print(f"[MOA_NODE] business_id={business_id}, session_id={session_id}")

    async def save_msg_to_long_term_mem(messages):
        if not session_id:
            print(f"[MOA_NODE] save_msg_to_long_term_mem SKIPPED — no session_id")
            return
        print(f"[MOA_NODE] save_msg_to_long_term_mem saving {len(messages)} messages to session={session_id}")
        await save_messages(business_id, session_id, messages, record_id=record_id or None)
        print(f"[MOA_NODE] save_msg_to_long_term_mem DONE")

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


    print(f"[MOA_NODE] Fetching conversation history and saving user message...")
    conversation_history, _ = await asyncio.gather(
       asyncio.create_task(fetch_short_msg_mem(limit=10)),  
       asyncio.create_task(
         save_msg_to_long_term_mem([{"role": "user", "content": user_message}])
         if user_message.strip() else asyncio.sleep(0)), 
       return_exceptions=True
    )
    print(f"[MOA_NODE] conversation_history loaded: {len(conversation_history) if conversation_history else 0} messages")

    result = await moa_orchestrator(
        user_request=user_message,
        business_id=business_id,
        conversation_messages=(conversation_history or [])[-12:],
        scopes=scopes,
        emit_callback=emit_callback
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
    print(f"[MOA_NODE] Saving assistant response to long-term mem: {text[:80] if text else ''}")
    await save_msg_to_long_term_mem([
            {"role": "assistant", "content": text},
    ])
    print(f"[MOA_NODE] === END === response saved")

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
