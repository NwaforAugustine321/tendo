import logging

from app.agents.models import Agent
from app.insight_recommender.config import get_dispatcher_config
from app.insight_recommender.delegation import DispatcherAgentTools
from app.insight_recommender.models import DispatcherOutput
from app.insight_recommender.persistence import persist_insights

logger = logging.getLogger(__name__)

_dispatcher_agent: Agent | None = None


def _get_dispatcher_agent() -> Agent:
    global _dispatcher_agent
    if _dispatcher_agent is None:
        _dispatcher_agent = Agent.from_spec("dispatcher")
    return _dispatcher_agent


async def dispatch_insights(reasoning_summary: str, business_id: str) -> DispatcherOutput | None:
    if not reasoning_summary or not reasoning_summary.strip():
        return None

    try:
        from app.lib.agent_executor import execute_task
        from app.insight_recommender.agents import ALL_INSIGHT_AGENTS

        config = get_dispatcher_config()
        agent = _get_dispatcher_agent()
        sub_agents = ALL_INSIGHT_AGENTS

        if not sub_agents:
            logger.warning("No sub-insight agents registered")
            return None

        delegation_tools = DispatcherAgentTools(agents=sub_agents, business_id=business_id)

        raw = await execute_task(
            agent=agent,
            description=reasoning_summary,
            tools=delegation_tools.tools(),
            expected_output=agent.expected_output,
            context=f"business_id: {business_id}",
            output_pydantic=DispatcherOutput,
            use_system_prompt=True,
            max_iter=config.dispatcher_max_iterations,
        )

        logger.info(f"Dispatcher output: {raw[:200]}")

        insight_texts = await delegation_tools.execute_pending()
        if insight_texts:
            count = await persist_insights(insight_texts, business_id, source_agent="dispatcher")
            logger.info(f"Dispatcher persisted {count} business insights")

        return DispatcherOutput(delegations=[])

    except Exception as e:
        logger.error(f"Dispatcher failed: {e}", exc_info=True)
        return None
