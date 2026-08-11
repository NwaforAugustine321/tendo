from typing import Any
from app.runtime import AgentRuntime, ToolBinder
from app.db.tools.profile_tools import get_profile_tools
from app.memory.tools import get_knowledge_tools
from app.toolsets.tool_context import ProviderTool
from app.toolsets.tool_proxy import ToolProxyToolset

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
            max_token=1024
        )
        self._proxy = None

    async def bind_tools(self, business_id: str, scopes: list[str] = []) -> None:
        all_tools = get_profile_tools(
            business_id) + get_knowledge_tools(business_id=business_id, scopes=scopes)

        self._proxy = ToolProxyToolset(
            id=f"knowledge-{business_id}",
            tools=[ProviderTool(t) for t in all_tools],
        )
        await self._proxy.setup()

        # Bind the two meta-tools (tool_search, call_tool) to the runtime
        self._runtime.bind_tool(self._proxy.to_langchain_tools())

    async def execute_agent(self, *args, **kwargs):
        return await self._runtime.execute(*args, **kwargs)
