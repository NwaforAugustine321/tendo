import asyncio
import logging
from app.agents.models import Agent
from app.lib.agent_tools import QueueingAgentTools
from app.insight_recommender.config import get_dispatcher_config
from app.memory.knowledge import BUSINESS_KNOWLEDGE_TOOLS

logger = logging.getLogger(__name__)


def get_insight_search_tools(business_id: str) -> list:
    return BUSINESS_KNOWLEDGE_TOOLS

async def execute_sub_agent(agent: Agent, business_id: str) -> str:
    from app.lib.agent_executor import execute_task

    config = get_dispatcher_config()
    tools = get_insight_search_tools(business_id)

    raw = await execute_task(
        agent=agent,
        description=f"You are tasked to analyze business data",
        tools=tools,
        expected_output=agent.expected_output,
        context=f"business_id: {business_id}",
        use_system_prompt=True,
        max_iter=config.sub_agent_max_iterations,
    )

    return raw.strip() if raw else ""


class Dispatcher:
    def __init__(self, agents: list[Agent], business_id: str):
        self._business_id = business_id
        self._queueing = QueueingAgentTools(agents=agents)

    def tools(self) -> list:
        return self._queueing.tools()

    async def execute_pending(self) -> list[str]:
        pending = self._queueing.pending_agents
        if not pending:
            return []

        config = get_dispatcher_config()
        semaphore = asyncio.Semaphore(config.max_concurrent_sub_agents)

        async def execute(agent: Agent) -> str:
            async with semaphore:
                try:
                    return await execute_sub_agent(agent, self._business_id)
                except Exception as e:
                    logger.warning(f"Sub-agent '{agent}' failed: {e}")
                    return ""

        tasks = [execute(agent) for agent in pending]
        results = await asyncio.gather(*tasks)

        self._queueing.clear_pending()
        return [r for r in results if r]
