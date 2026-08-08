from __future__ import annotations

import asyncio
import logging
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from app.manifests import load_manifest
from app.runtime import AgentRuntime, ToolBinder

logger = logging.getLogger(__name__)

try:
    from app.agents.models import Agent
    agent_spec = Agent.from_spec("planner")
except Exception:
    agent_spec = None





class SelectedAgent(BaseModel):
    agent_id: str =  Field(default_factory=str, description="Agent id.")
    depends_on: list =  Field(default_factory=list[str], description="List of agent_id the agent depend on")
    message_input: str = Field(..., min_length=1, description="Clear instruction for what the agent must accomplish")

class AgentSelectionOutput(BaseModel):
    agents: list[SelectedAgent] = Field(default_factory=list, description="List of agents to handle the request. Each has agent_id, execution_context, and depends_on.")
    shared_constraints: str = Field(default_factory=str, description="Shared constraints for all agents execution")

class PlanningError(Exception):
    def __init__(self, message: str, manifest: str | None = None):
        super().__init__(message)
        self.manifest = manifest


_AGENT_REGISTRY = None
_active_session = None
_active_business_id = ""
_active_emit_callback = None
_active_session_id = ""


def set_active_session(session=None, business_id: str = "", emit_callback=None, session_id: str = ""):
    global _active_session, _active_business_id, _active_emit_callback, _active_session_id
    _active_session = session
    _active_business_id = business_id
    _active_emit_callback = emit_callback
    _active_session_id = session_id


def _get_registry():
    global _AGENT_REGISTRY
    if _AGENT_REGISTRY is None:
        from app.agents.specs.domain import TransactionsAgent, InventoryAgent, KnowledgeAgent
        _AGENT_REGISTRY = {
            "transaction_agent": TransactionsAgent(),
            "inventory_agent": InventoryAgent(),
            "general_information_agent": KnowledgeAgent(),
        }
    return _AGENT_REGISTRY


@tool
async def delegate_to_agents(
    agents: list[SelectedAgent],
    shared_constraints: str = "",
) -> str:
    """Delegate tasks to specialized sub-agents for execution.

    Args:
        agents: List of agent assignments. Each must have:
            - agent_id: One of "transaction_agent", "inventory_agent", "general_information_agent"
            - message_input: Clear instruction for what the agent must accomplish
            - depends_on: List of agent_ids this agent depends on
        shared_constraints: Constraints that apply to all agents.

    Return:
        str.
    """
    registry = _get_registry()

    has_dependencies = any(
        len(a.depends_on) > 0 for a in agents if hasattr(a, 'depends_on')
    )

    agent_dicts = [a.model_dump() if hasattr(a, 'model_dump') else a for a in agents]

    if has_dependencies:
        asyncio.create_task(_run_sequential_and_speak(agent_dicts, registry, shared_constraints))
    else:
        asyncio.create_task(_run_parallel_and_speak(agent_dicts, registry, shared_constraints))

    agent_names = [a.get("agent_id", "") for a in agent_dicts]
    
    return "Task delegated to specialist agents. They are processing now. Provide a brief acknowledgment to the user."


async def _run_parallel(agents: list[dict], registry: dict, shared_constraints: str) -> str:
    async def run_one(agent_info: dict) -> str:
        agent_id = agent_info.get("agent_id", "")
        message_input = agent_info.get("message_input", "")

        agent = registry.get(agent_id)
        if agent is None:
            return f"Unknown agent: {agent_id}"

        try:
            task = f"{message_input}\n{shared_constraints}".strip()
            agent.bind_tools(_active_business_id, scopes=[])
            result = await agent.execute_agent(task)
            if isinstance(result, str):
                return result
            if hasattr(result, 'result') and hasattr(result.result, 'response'):
                return result.result.response
            return str(result)
        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {e}")
            return f"Error from {agent_id}: {str(e)}"

    tasks = [run_one(a) for a in agents]
    results = await asyncio.gather(*tasks)
    return "\n\n".join(r for r in results if r)


async def _run_sequential(agents: list[dict], registry: dict, shared_constraints: str) -> str:
    results = []
    for agent_info in agents:
        agent_id = agent_info.get("agent_id", "")
        message_input = agent_info.get("message_input", "")

        agent = registry.get(agent_id)
        if agent is None:
            results.append(f"Unknown agent: {agent_id}")
            continue

        try:
            task = f"{message_input}\n{shared_constraints}".strip()
            agent.bind_tools(_active_business_id, scopes=[])
            result = await agent.execute_agent(task)
            if isinstance(result, str):
                results.append(result)
            elif hasattr(result, 'result') and hasattr(result.result, 'response'):
                results.append(result.result.response)
            else:
                results.append(str(result))
        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {e}")
            results.append(f"Error from {agent_id}: {str(e)}")

    return "\n\n".join(r for r in results if r)


async def _run_parallel_and_speak(agents: list[dict], registry: dict, shared_constraints: str):
    result = await _run_parallel(agents, registry, shared_constraints)
    if result:
        if _active_session:
            _active_session.say(result)
        if _active_emit_callback:
            await _active_emit_callback("message", {
                "type": "message",
                "data": {"response": result, "msg_type": "answer"},
            })
        if _active_session_id and _active_business_id:
            from app.db.tools.messages import save_messages
            await save_messages(_active_business_id, _active_session_id, [{"role": "assistant", "content": result}])


async def _run_sequential_and_speak(agents: list[dict], registry: dict, shared_constraints: str):
    result = await _run_sequential(agents, registry, shared_constraints)
    if result:
        if _active_session:
            _active_session.say(result)
        if _active_emit_callback:
            await _active_emit_callback("message", {
                "type": "message",
                "data": {"response": result, "msg_type": "answer"},
            })
        if _active_session_id and _active_business_id:
            from app.db.tools.messages import save_messages
            await save_messages(_active_business_id, _active_session_id, [{"role": "assistant", "content": result}])


class Planner:

    def __init__(self) -> None:
        manifests = self._load_manifests()

        system_context = (
            f"{manifests['agents']}\n\n"
            # f"{manifests['skills']}\n\n"
            # f"{manifests['knowledge']}\n\n"
            # f"{manifests['tools']}\n\n"
        )

        self._runtime = AgentRuntime(
            tool_binder=ToolBinder(),
            agent=agent_spec,
            tools=[delegate_to_agents],
            # allowed_input_guardrail=True,
            system_prompt=system_context,
        )

    async def run(self, user_request: str, conversation_messages: list[dict] | None = None, messages: list | None = None):
       
        raw = await self._runtime.execute(
            user_request,
            chat_history=conversation_messages or [],
            use_plan_mode=True,
            messages=messages,
        )
        return AIMessage(content=raw or "")

    async def plan(self, user_request: str, conversation_messages: list[dict] | None = None):
        from app.planner.models import ExecutionOrder, ExecutionPlan
        from app.contexts.models import SharedContext

        result_msg = await self.run(user_request, conversation_messages)
        response = result_msg.content

        shared_ctx = SharedContext(
            user_request=user_request,
            conversation_messages=conversation_messages or [],
            shared_constraints="",
        )
        return ExecutionPlan(
            participating_agents=[],
            execution_order=ExecutionOrder.PARALLEL,
            shared_context=shared_ctx,
            unresolvable=True,
            unresolvable_reason=response,
        )

    def _load_manifests(self) -> dict[str, str]:
        manifest_names = ["agents", "skills", "tools", "knowledge"]
        manifests: dict[str, str] = {}
        for name in manifest_names:
            try:
                manifests[name] = load_manifest(name)
            except FileNotFoundError:
                raise PlanningError(f"Manifest '{name}' is unreachable.", manifest=name)
        return manifests
