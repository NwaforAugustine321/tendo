"""Agent delegation tools — DelegateWorkTool and AskQuestionTool.

Used by the MOA (manager agent) to delegate tasks to specialist agents
or ask them questions. Mirrors CrewAI's AgentTools pattern.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.lib.i18n import _get_i18n

logger = logging.getLogger(__name__)


def _i18n_tools(key: str) -> str:
    """Get a tools translation string."""
    i18n = _get_i18n()
    return i18n.get(f"tools.{key}")


def _i18n_errors(key: str) -> str:
    """Get an errors translation string."""
    i18n = _get_i18n()
    return i18n.get(f"errors.{key}")


def _sanitize_name(name: str) -> str:
    """Normalize agent role name for matching."""
    if not name:
        return ""
    normalized = " ".join(name.split())
    return normalized.replace('"', "").casefold()


def _find_agent(agents: Sequence[Any], coworker: str) -> Any | None:
    """Find an agent by role name (fuzzy matching).
    """
    sanitized = _sanitize_name(coworker)
    if not sanitized:
        return None

    # Strip trailing punctuation from coworker name
    sanitized = sanitized.rstrip(".,!?;:")

    # 1. Exact match
    for agent in agents:
        if _sanitize_name(agent) == sanitized:
            return agent

    return None


def _coworker_list(agents: Sequence[Any]) -> str:
    """Format list of available coworkers."""
    return "\n".join(f"- {_sanitize_name(a.role)}" for a in agents)


class DelegateWorkInput(BaseModel):
    """Input schema for DelegateWorkTool."""

    task: str = Field(..., description="The task to delegate")
    context: str = Field(..., description="The context for the task")
    coworker: str = Field(
        ..., description="The role/name of the coworker to delegate to"
    )


class AskQuestionInput(BaseModel):
    """Input schema for AskQuestionTool."""

    question: str = Field(..., description="The question to ask")
    context: str = Field(..., description="The context for the question")
    coworker: str = Field(..., description="The role/name of the coworker to ask")


def _delegate_work(agents: Sequence[Any], task: str, context: str, coworker: str) -> str:
    """Execute delegation to a coworker agent.

    Returns a routing signal that the MOA node detects to set routed_domain.
    Format: __ROUTE__:{agent_role_lowercase}
    """
    agent = _find_agent(agents, coworker)
    if not agent:
        return _i18n_errors("agent_tool_unexisting_coworker").format(
            coworkers=_coworker_list(agents)
        )

    # Return routing signal — MOA node will parse this and set routed_domain
    role_key = _sanitize_name(agent).replace(" ", "_")
    return f"__ROUTE__:{role_key}"


def _ask_question(agents: Sequence[Any], question: str, context: str, coworker: str) -> str:
    """Ask a question to a coworker agent.

    Returns a routing signal same as delegation — the specialist will handle it.
    """
    agent = _find_agent(agents, coworker)
    if not agent:
        return _i18n_errors("agent_tool_unexisting_coworker").format(
            coworkers=_coworker_list(agents)
        )

    role_key = _sanitize_name(agent).replace(" ", "_")
    return f"__ROUTE__:{role_key}"


class AgentTools:
    """Manager class for agent-related tools.

    Creates DelegateWorkTool and AskQuestionTool that allow the manager
    agent (MOA) to delegate tasks to specialist agents.

    Usage:
        from app.agents.models import Agent
        agents = [Agent.from_spec("domain/inventory"), Agent.from_spec("domain/transactions")]
        tools = AgentTools(agents=agents).tools()
    """

    def __init__(self, agents: Sequence[Any]) -> None:
        self.agents = agents

    def tools(self) -> list[BaseTool]:
        """Get all available agent tools."""
        coworkers = ", ".join(f"{agent}" for agent in self.agents)

        delegate_description = _i18n_tools("delegate_work").format(coworkers=coworkers)
        ask_description = _i18n_tools("ask_question").format(coworkers=coworkers)

        agents = self.agents

        def do_delegate(task: str, context: str, coworker: str) -> str:
            return _delegate_work(agents, task, context, coworker)

        def do_ask(question: str, context: str, coworker: str) -> str:
            return _ask_question(agents, question, context, coworker)

        delegate_tool = StructuredTool.from_function(
            func=do_delegate,
            name="delegate_work_to_coworker",
            description=delegate_description,
            args_schema=DelegateWorkInput,
        )

        ask_tool = StructuredTool.from_function(
            func=do_ask,
            name="ask_question_to_coworker",
            description=ask_description,
            args_schema=AskQuestionInput,
        )

        return [delegate_tool, ask_tool]


class QueueingAgentTools:
    """Delegation tools that queue agents for parallel execution.

    Unlike AgentTools (which returns __ROUTE__ signals for graph routing),
    this class collects delegated agents into a pending list for later
    concurrent execution.

    Usage:
        tools = QueueingAgentTools(agents=sub_agents)
        # ... agent uses delegate_work_to_coworker during ReAct loop ...
        pending = tools.pending_agents  # agents queued for execution
    """

    def __init__(self, agents: Sequence[Any]) -> None:
        self.agents = agents
        self._pending: list[Any] = []

    @property
    def pending_agents(self) -> list[Any]:
        return self._pending

    def clear_pending(self) -> None:
        self._pending.clear()

    def tools(self) -> list[BaseTool]:
        coworkers = ", ".join(f"{agent.role}" for agent in self.agents)
        delegate_description = _i18n_tools("delegate_work").format(coworkers=coworkers)
        ask_description = _i18n_tools("ask_question").format(coworkers=coworkers)
        agents = self.agents

        async def do_delegate(task: str, context: str, coworker: str) -> str:
            agent = _find_agent(agents, coworker)
            if not agent:
                return _i18n_errors("agent_tool_unexisting_coworker").format(
                    coworkers=_coworker_list(agents)
                )
            self._pending.append(agent)
            return f"Queued '{agent.role}' for parallel execution."

        async def do_ask(question: str, context: str, coworker: str) -> str:
            agent = _find_agent(agents, coworker)
            if not agent:
                return _i18n_errors("agent_tool_unexisting_coworker").format(
                    coworkers=_coworker_list(agents)
                )
            self._pending.append(agent)
            return f"Queued '{agent.role}' for parallel execution."

        delegate_tool = StructuredTool.from_function(
            coroutine=do_delegate,
            name="delegate_work_to_coworker",
            description=delegate_description,
            args_schema=DelegateWorkInput,
        )

        ask_tool = StructuredTool.from_function(
            coroutine=do_ask,
            name="ask_question_to_coworker",
            description=ask_description,
            args_schema=AskQuestionInput,
        )

        return [delegate_tool, ask_tool]
