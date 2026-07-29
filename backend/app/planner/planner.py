

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
from app.lib.prompts import build_execution_prompt
from app.lib.task_prompt import prepare_task_prompt
from app.manifests import load_manifest
from app.planner.models import AgentAssignment, ExecutionOrder, ExecutionPlan
from app.runtime import AgentRuntime, ToolBinder
from app.llm.client import get_client

logger = logging.getLogger(__name__)

_agent = PlannerAgent()




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
    response: str = Field(default_factory=str, description="Direct Response if no sub agent is selected")


class PlanningError(Exception):
    def __init__(self, message: str, manifest: str | None = None):
        super().__init__(message)
        self.manifest = manifest


class Planner:

    def __init__(self) -> None:
        
        self._agent = AgentRuntime(
            tool_binder=ToolBinder(),
            agent=_agent,
            expected_output='Return json output',
            output_pydantic=AgentSelectionOutput,
        )

    async def plan(
        self,
        user_request: str,
        conversation_messages: list[dict] | None = None,
    ) -> ExecutionPlan:
        manifests = self._load_manifests()
    
        result = await self._select_agents(user_request, manifests,conversation_messages)
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


    async def _select_agents(self, user_request: str, manifests: str, chat_history: list[Any] = []) -> list[dict[str, Any]]:
        agents_manifest = manifests["agents"]
        skills_manifest = manifests["skills"]
        knowledge_manifest = manifests["knowledge"]
        tools_manifest = manifests['tools'] 

        context = (
            f"User Question:\n\n{user_request}\n\n"
            f"Available Agents:\n\n{agents_manifest}\n\n"
            f"Available Skills:\n\n{skills_manifest}\n\n"
            f"Available Knowledge:\n\n{knowledge_manifest}\n\n"
            f"Available Tools:\n\n{tools_manifest}\n\n"
        )

  

        # raw = await self._agent.execute(user_request,context=context)
        
        raw = await self._agent.execute(context, chat_history=chat_history)
        
       
        try:
            raw_text = raw.result.response if hasattr(raw, 'result') else str(raw)
            response = parse_json_output(raw_text)
        except (ValueError, TypeError):
            logger.warning("Failed to parse agent selection response: %s", response[:200])
            return  {
                "agents": [],
                "shared_constraints": '',
                "response": ''
            }

        agents = response.get("agents", [])
        shared_constraints = response.get("shared_constraints", "")
        direct_response = response.get("response", "")
 
        if not isinstance(agents, list):
            return {
                "agents": [],
                "shared_constraints": "",
                "response": direct_response
            }

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
