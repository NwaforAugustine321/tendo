import logging

from app.agents.models import Agent
from app.insight_recommender.config import get_dispatcher_config
from app.insight_recommender.delegation import Dispatcher
from app.insight_recommender.models import DispatcherOutput
from app.insight_recommender.persistence import persist_insights
from app.lib.i18n import _get_i18n

logger = logging.getLogger(__name__)

_dispatcher_agent: Agent | None = None


def _get_dispatcher_agent() -> Agent:
    """Create dispatcher agent"""
    global _dispatcher_agent
    if _dispatcher_agent is None:
        i18n = _get_i18n()
        _dispatcher_agent = Agent(
            role=i18n.get("hierarchical_manager_agent.role"),
            goal=i18n.get("hierarchical_manager_agent.goal"),
            backstory=i18n.get("hierarchical_manager_agent.backstory"),
            skill=Agent.from_spec("dispatcher").skill,
        )
    return _dispatcher_agent


all_insight_agents = ['business_health', 'customer', 'inventory', 'operations', 'recommendation', 'risk', 'trend']


async def dispatch_insights(reasoning_summary: str, business_id: str) -> DispatcherOutput | None:
    if not reasoning_summary or not reasoning_summary.strip():
        return None

    try:
        from app.lib.agent_executor import execute_task

        config = get_dispatcher_config()
        agent = _get_dispatcher_agent()
        sub_agents = all_insight_agents

        if not sub_agents:
            logger.warning("No sub-insight agents registered")
            return None

        dispatcher = Dispatcher(agents=sub_agents, business_id=business_id)

        raw = await execute_task(
            agent=agent,
            description=reasoning_summary,
            tools=dispatcher.tools(),
            expected_output=agent.expected_output,
            context=f"business_id: {business_id}",
            output_pydantic=DispatcherOutput,
            use_system_prompt=True,
            max_iter=config.dispatcher_max_iterations,
        )

        logger.info(f"Dispatcher output: {raw[:200]}")

        insight_texts = await dispatcher.execute_pending()
        if insight_texts:
            count = await persist_insights(insight_texts, business_id, source_agent="dispatcher")
            logger.info(f"Dispatcher persisted {count} business insights")

        return DispatcherOutput(delegations=[])

    except Exception as e:
        logger.error(f"Dispatcher failed: {e}", exc_info=True)
        return None
