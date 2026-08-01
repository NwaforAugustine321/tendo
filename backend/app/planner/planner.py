

from __future__ import annotations
import logging
from typing import Any
from pydantic import BaseModel, Field
from app.agents.specs.planner.agent import PlannerAgent
from app.contexts.models import (
    Constraint,
    ExecutionContext,
    SharedContext,
)
from app.lib.json_parser import parse_json_output
from app.lib.prompts import prepare_task_prompt
from app.manifests import load_manifest
from app.planner.models import AgentAssignment, ExecutionOrder, ExecutionPlan
from app.runtime import AgentRuntime, ToolBinder
from app.llm.client import get_client
from app.guardrails import GuardrailManager, GuardrailConfig
from app.lib.i18n import _get_i18n
from typing import Union

def _planne(key: str) -> str:
    i18n = _get_i18n()
    return i18n.get(f"planning.{key}")



logger = logging.getLogger(__name__)

try:
    from app.agents.models import Agent
    agent_spec = Agent.from_spec("planner")
except Exception:
    agent_spec = None



class ExecutionContextOutput(BaseModel):
    objective: str = Field(..., min_length=1, description="Clear instruction for what the agent must accomplish")
    tools: list = Field(default_factory=list, description="Tools needed for this request")
    knowledge: list = Field(default_factory=list, description="Relevant knowledge collections")
    skills: list = Field(default_factory=list, description="Any needed skills")


class SelectedAgent(BaseModel):
    agent_id: str =  Field(default_factory=str, description="Agent id.")
    depends_on: list =  Field(default_factory=list[str], description="List of agent_id the agent depend on")
    execution_context: ExecutionContextOutput = Field(description="The execution context for the agent")
    constraints: str = Field(default_factory=str, description="Constraints for execution")

class AgentSelectionOutput(BaseModel):
    agents: list[SelectedAgent] = Field(default_factory=list, description="List of agents to handle the request. Each has agent_id, execution_context, and depends_on.")
    shared_constraints: str = Field(default_factory=str, description="Shared constraints for all agents execution")
   
class CoordinatorResponse(BaseModel):
    is_task_trigger: bool = Field(
        description="Set to True if this requires sub-agents/planning. Set to False if this is just normal conversation."
    )
    conversation_response: Union[str, None] = Field(
        default=None, 
        description="The natural language response to the user. ONLY populate this if is_task_trigger is False."
    )
    agent_selection: Union[AgentSelectionOutput, None]  = Field(
        default=None, 
        description="The structured plan for sub-agents. ONLY populate this if is_task_trigger is True."
    )


class PlanningError(Exception):
    def __init__(self, message: str, manifest: str | None = None):
        super().__init__(message)
        self.manifest = manifest


class Planner:

    def __init__(self) -> None:
        
        # self._system_prompt = _planne("system_prompt")
        
        manifests = self._load_manifests()

        agents_manifest = manifests["agents"]
        skills_manifest = manifests["skills"]
        knowledge_manifest = manifests["knowledge"]
        tools_manifest = manifests['tools'] 

        tools = (
            f"{agents_manifest}\n\n"
            f"{skills_manifest}\n\n"
            f"{knowledge_manifest}\n\n"
            f"{tools_manifest}\n\n"
        )

        self._runtime = AgentRuntime(
            tool_binder=ToolBinder(),
            agent=agent_spec,
            expected_output='Return json output',
            output_pydantic=CoordinatorResponse,
            allowed_input_guardrail=True,
            # use_system_prompt=True,
            system_prompt=tools
        )




    async def plan(
        self,
        user_request: str,
        conversation_messages: list[dict] | None = None,
    ) -> ExecutionPlan:
        
    
        result = await self._select_agents(user_request,conversation_messages)
        selected = result.get('agents', [])
        shared_constraints = result.get('shared_constraints', '')
        response = result.get('response', '')
        

        if not selected:
            shared_ctx = SharedContext(
                user_request=user_request,
                conversation_messages=conversation_messages or [],
                shared_constraints=shared_constraints,
            )
            return ExecutionPlan(
                participating_agents=[],
                execution_order=ExecutionOrder.PARALLEL,
                shared_context=shared_ctx,
                unresolvable=True,
                unresolvable_reason=response,
            )

        assignments: list[Any] = []
        
       
        for agent_info in selected:
            agent_id = agent_info["agent_id"]
            depends_on = agent_info.get("depends_on", [])
            execution_context = agent_info.get("execution_context", [])
            constraints = agent_info.get("constraints", '')

            assignments.append(
                AgentAssignment(
                    agent_id=agent_id,
                    execution_context=execution_context,
                    depends_on=depends_on,
                    constraints=constraints
                )
            )

        execution_order = self._determine_order(assignments)

        shared_ctx = SharedContext(
            user_request=user_request,
            conversation_messages=conversation_messages or [],
            shared_constraints= shared_constraints,
        )

        return ExecutionPlan(
            participating_agents=assignments,
            execution_order=execution_order,
            shared_context=shared_ctx,
           
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


    async def _select_agents(self, user_request: str, chat_history: list[Any] = []) -> list[dict[str, Any]]:
    
        raw = await  self._runtime.execute(user_request,chat_history=chat_history,use_plan_mode=True,task_msg_check=user_request)
    
       
        try:
            raw_text = raw.result.response if hasattr(raw, 'result') else str(raw)
            response = parse_json_output(raw_text)
        except (ValueError, TypeError):
            logger.warning("Failed to parse agent selection response")
            return  {
                "agents": [],
                "shared_constraints": '',
                "response": ''
            }

        if not isinstance(response, dict):
            return {
                "agents": [],
                "shared_constraints": '',
                "response": str(response) if response else ''
            }

        agent_selection = response.get("agent_selection", None)
        shared_constraints = response.get("shared_constraints", "")
        direct_response = response.get("conversation_response", "")
        is_task_trigger = response.get("is_task_trigger", "")

        if not is_task_trigger:
            return {
                "agents": [],
                "shared_constraints": "",
                "response": direct_response
            }           
        else:
           if not isinstance(agent_selection, dict):
               return {
                   "agents": [],
                   "shared_constraints": shared_constraints,
                   "response": direct_response
               }
           agents = agent_selection.get("agents", [])
           return {
            "agents": [a for a in agents if isinstance(a, dict) and "agent_id" in a],
            "shared_constraints": shared_constraints,
            "response": direct_response
           }


    @staticmethod
    def _determine_order(assignments: list[AgentAssignment]) -> ExecutionOrder:
        if len(assignments) <= 1:
            return ExecutionOrder.SEQUENTIAL
        has_dependency = any(len(a.depends_on) > 0 for a in assignments)
        return ExecutionOrder.SEQUENTIAL if has_dependency else ExecutionOrder.PARALLEL
