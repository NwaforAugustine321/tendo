from typing import Any

from app.execution.models import Result
from app.runtime import AgentRuntime, ToolBinder


try:
    from app.agents.models import Agent
    agent_spec = Agent.from_spec("moa")
except Exception:
    agent_spec = None


class MoaAgent:

    def __init__(self):
        self._runtime = AgentRuntime(
                agent=agent_spec,
                tool_binder=ToolBinder(),
        )

    def bind_tools(self, business_id: str, scopes: list[str] = []) -> list[Any]:
        self._runtime.bind_tool([])

    async def execute_agent(self, *args, **kwargs):
        return await self._runtime.execute(*args, **kwargs)
