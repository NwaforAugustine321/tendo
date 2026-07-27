"""Planner — intelligence layer that builds ExecutionPlans from user requests."""

from __future__ import annotations

import logging
from typing import Any

from app.contexts.models import (
    Constraint,
    ExecutionContext,
    KnowledgeEntry,
    OutputSpec,
    SharedContext,
    SkillEntry,
    ToolReference,
)
from app.lib.json_parser import parse_json_output
from app.manifests import load_manifest
from app.planner.models import AgentAssignment, ExecutionOrder, ExecutionPlan
from app.runtime import AgentRuntime, ToolBinder

logger = logging.getLogger(__name__)


_AGENT_SELECTION_PROMPT = """\
Given a user request and an Agent Manifest, decide which agents should participate.

## Agent Manifest
{agents_manifest}

## User Request
{user_request}

Rules:
- Select ONLY agents whose domain or capabilities match the request intent.
- If no agent matches, return empty agents list.
- If an agent depends on another agent's output, list the dependency in "depends_on" as agent_ids.
- Respond with valid JSON only: {{"agents": [{{"agent_id": "...", "reason": "...", "depends_on": []}}]}}
"""

_CONTEXT_BUILDING_PROMPT = """\
Given an agent, a user request, and the available manifests, decide what skills, knowledge, and tools this agent needs.

## Agent
ID: {agent_id}

## User Request
{user_request}

## Skills Manifest
{skills_manifest}

## Knowledge Manifest
{knowledge_manifest}

## Tools Manifest
{tools_manifest}

RESPOND WITH ONLY A VALID JSON OBJECT. NO PROSE. NO MARKDOWN. NO EXPLANATION.
The JSON must contain ALL of these fields:
{{
  "objective": "<clear instruction for what the agent must accomplish>",
  "skills": ["<matching skill ids>"],
  "knowledge": ["<matching collection ids>"],
  "tools": ["<matching tool ids>"],
  "constraints": []
}}

The "objective" field is REQUIRED and must be a clear, non-empty instruction.
Output ONLY the JSON object, nothing else.
"""


class PlanningError(Exception):
    def __init__(self, message: str, manifest: str | None = None):
        super().__init__(message)
        self.manifest = manifest


class Planner:
    """Intelligence layer that builds ExecutionPlans from user requests."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm
        self._runtime = AgentRuntime(
            llm=llm,
            tool_binder=ToolBinder(),
            max_iter=5,
            max_validation_retries=1,
        )

    async def plan(
        self,
        user_request: str,
        business_id: str,
        uploaded_files: list[str] | None = None,
        conversation_messages: list[dict] | None = None,
        shared_constraints: list[Constraint] | None = None,
        scope: str = "knowledge",
        record_id: str = "",
    ) -> ExecutionPlan:
        manifests = self._load_manifests()


        agents_manifest = manifests["agents"]

        selected = await self._select_agents(user_request, agents_manifest)

        if not selected:
            shared_ctx = SharedContext(
                user_request=user_request,
                uploaded_files=uploaded_files or [],
                conversation_messages=conversation_messages or [],
                business_id=business_id,
                shared_constraints=shared_constraints or [],
            )
            return ExecutionPlan(
                participating_agents=[],
                execution_order=ExecutionOrder.PARALLEL,
                shared_context=shared_ctx,
                unresolvable=True,
                unresolvable_reason="No agent in the manifest matches the request intent.",
            )

        assignments: list[AgentAssignment] = []
        for agent_info in selected:
            agent_id = agent_info["agent_id"]
            depends_on = agent_info.get("depends_on", [])
            execution_context = await self._build_execution_context(
                agent_id=agent_id,
                user_request=user_request,
                business_id=business_id,
                manifests=manifests,
                scope=scope,
            )
            assignments.append(
                AgentAssignment(
                    agent_id=agent_id,
                    execution_context=execution_context,
                    depends_on=depends_on,
                )
            )

        execution_order = self._determine_order(assignments)

        shared_ctx = SharedContext(
            user_request=user_request,
            uploaded_files=uploaded_files or [],
            conversation_messages=conversation_messages or [],
            business_id=business_id,
            shared_constraints=shared_constraints or [],
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

    @staticmethod
    def _filter_tools_by_domain(tools_manifest: str, agent_id: str) -> str:
        """Filter tools manifest to only show tools whose Domain includes the agent_id."""
        sections = tools_manifest.split("\n## ")
        header = sections[0] if sections else "# Tool Manifest\n"
        filtered = [header]

        for section in sections[1:]:
            lines = section.split("\n")
            for line in lines:
                if line.strip().startswith("- **Domain**:"):
                    domains = line.split(":", 1)[1].strip().lower()
                    domain_list = [d.strip() for d in domains.split(",")]
                    if agent_id.lower() in domain_list:
                        filtered.append("## " + section)
                    break

        return "\n".join(filtered)

    @staticmethod
    def _filter_manifest_by_scope(agents_manifest: str, scope: str) -> str:
        """Filter the agent manifest to only show agents relevant to the scope.
        
        Scopes map to domains:
        - knowledge → knowledge agent only
        - record → knowledge agent only
        - transactions → transactions agent only
        - inventory → inventory agent only
        - onboarding → onboarding agent only
        - other → all agents (planner decides)
        """
        scope_to_domains = {
            "knowledge": ["knowledge"],
            "record": ["knowledge"],
            "transactions": ["transactions"],
            "inventory": ["inventory"],
            "onboarding": ["onboarding"],
        }

        allowed_domains = scope_to_domains.get(scope)
        if not allowed_domains:
            return agents_manifest

        # Parse markdown and filter sections
        lines = agents_manifest.split("\n")
        filtered_lines: list[str] = []
        include_section = False

        for line in lines:
            if line.startswith("## "):
                agent_id = line[3:].strip()
                include_section = agent_id in allowed_domains
            if line.startswith("# "):
                filtered_lines.append(line)
                continue
            if include_section:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    async def _select_agents(self, user_request: str, agents_manifest: str) -> list[dict[str, Any]]:
        prompt = _AGENT_SELECTION_PROMPT.format(
            agents_manifest=agents_manifest,
            user_request=user_request,
        )

        raw = await self._invoke_runtime(prompt)

        try:
            data = parse_json_output(raw)
        except (ValueError, TypeError):
            logger.warning("Failed to parse agent selection response: %s", raw[:200])
            return []

        agents = data.get("agents", [])
        if not isinstance(agents, list):
            return []
        return [a for a in agents if isinstance(a, dict) and "agent_id" in a]

    async def _build_execution_context(
        self,
        agent_id: str,
        user_request: str,
        business_id: str,
        manifests: dict[str, str],
        scope: str = "knowledge",
        max_retries: int = 3,
    ) -> ExecutionContext:
        # Filter tools manifest to only show tools for the agent's domain
        filtered_tools = self._filter_tools_by_domain(manifests["tools"], agent_id)

        prompt = _CONTEXT_BUILDING_PROMPT.format(
            agent_id=agent_id,
            user_request=user_request,
            skills_manifest=manifests["skills"],
            knowledge_manifest=manifests["knowledge"],
            tools_manifest=filtered_tools,
        )

        for attempt in range(max_retries):
            raw = await self._invoke_runtime(prompt)

            try:
                data = parse_json_output(raw)
            except (ValueError, TypeError):
                logger.warning("Attempt %d: failed to parse context for agent '%s'", attempt + 1, agent_id)
                continue

            objective = data.get("objective", "").strip()
            if not objective:
                logger.warning("Attempt %d: objective empty for agent '%s'", attempt + 1, agent_id)
                continue

            skills = []
            for s in data.get("skills", []):
                if isinstance(s, dict) and "skill_id" in s:
                    skills.append(SkillEntry(**s))
                elif isinstance(s, str):
                    skills.append(SkillEntry(skill_id=s, category=s, content=s))

            knowledge = []
            for k in data.get("knowledge", []):
                if isinstance(k, dict) and "collection_id" in k:
                    knowledge.append(KnowledgeEntry(**k))
                elif isinstance(k, str):
                    knowledge.append(KnowledgeEntry(collection_id=k, domain=agent_id, content=k))

            tools = []
            for t in data.get("tools", []):
                if isinstance(t, dict) and "tool_id" in t:
                    tools.append(ToolReference(**t))
                elif isinstance(t, str):
                    tools.append(ToolReference(tool_id=t, capability=t))

            expected_output_data = data.get("expected_output", {"format": "json"})
            expected_output = OutputSpec(
                format=expected_output_data.get("format", "json"),
                schema_ref=expected_output_data.get("schema_ref"),
                required_fields=expected_output_data.get("required_fields", []),
            )

            constraints = [
                Constraint(**c)
                for c in data.get("constraints", [])
                if isinstance(c, dict) and "name" in c and "condition" in c
            ]

            return ExecutionContext(
                objective=objective,
                skills=skills,
                knowledge=knowledge,
                available_tools=tools,
                expected_output=expected_output,
                constraints=constraints,
            )

        raise PlanningError(f"Failed to build execution context for agent '{agent_id}' after {max_retries} retries.")

    async def _invoke_runtime(self, prompt: str) -> str:
        """Use AgentRuntime's invoke loop with expected JSON output validation."""
        from pydantic import BaseModel as PModel, Field as PField

        class _PlannerOutput(PModel):
            objective: str
            skills: list = PField(default_factory=list)
            knowledge: list = PField(default_factory=list)
            tools: list = PField(default_factory=list)
            constraints: list = PField(default_factory=list)

        self._runtime._messages = [
            {"role": "system", "content": "You are a JSON-only responder. Output ONLY valid JSON. No prose, no markdown, no explanation."},
            {"role": "user", "content": prompt},
        ]
        self._runtime._iterations = 0
        self._runtime._tool_call_history = set()
        self._runtime._response_model = _PlannerOutput
        result = await self._runtime._invoke_loop()
        self._runtime._response_model = None
        return result

    @staticmethod
    def _determine_order(assignments: list[AgentAssignment]) -> ExecutionOrder:
        has_dependency = any(len(a.depends_on) > 0 for a in assignments)
        return ExecutionOrder.SEQUENTIAL if has_dependency else ExecutionOrder.PARALLEL
