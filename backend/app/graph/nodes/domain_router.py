"""Domain Router node — sets routing state for the graph edge to dispatch to specialists."""

import logging

from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def domain_router_node(state: GraphState) -> dict:
    """Set routing state — the conditional edge handles actual dispatch."""
    routed = state.get("routed_domain") or ""
    logger.info(f"Domain router: setting workflow_owner to '{routed}'")

    return {
        "current_agent": routed,
        "workflow_owner": routed,
        "return_to": routed,
        "routed_domain": None,  # Clear so MOA doesn't re-route
    }
