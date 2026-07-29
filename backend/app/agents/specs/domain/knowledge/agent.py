from typing import Any
from app.runtime import AgentRuntime, ToolBinder
from app.execution.models import Result
from app.db.tools.profile_tools import get_profile_tools
from app.memory.tools import get_knowledge_tools

try:
    from app.agents.models import Agent
    agent_spec = Agent.from_spec("domain/knowledge")
except Exception:
    agent_spec = None


class KnowledgeAgent:

    def __init__(self):
        self._runtime = AgentRuntime(
                agent=agent_spec,
                tool_binder=ToolBinder(),
        )

    def bind_tools(self, business_id: str, scopes: list[str] = []) -> list[Any]:
        self._runtime.bind_tool(get_profile_tools(business_id) + get_knowledge_tools(business_id=business_id, scopes=scopes))

    async def execute_agent(self, *args, **kwargs):
        return await self._runtime.execute(*args, **kwargs)
