"""Domain Router node — dispatches to the correct sub-agent handler dynamically."""

import logging

from app.graph.nodes.onboarding import onboarding_node
from app.models.state import GraphState

logger = logging.getLogger(__name__)

# Handler registry — add new sub-agents here
HANDLERS = {
    "onboarding": onboarding_node,
}


async def domain_router_node(state: GraphState) -> dict:
    """Dispatch to the correct sub-agent based on routed_domain."""
    routed = state.get("routed_domain") or ""
    handler = HANDLERS.get(routed)

    if not handler:
        logger.warning(f"Domain router: no handler for '{routed}'")
        return {"routed_domain": None, "domain_result": {}}

    logger.info(f"Domain router: dispatching to '{routed}'")
    return await handler(state)
