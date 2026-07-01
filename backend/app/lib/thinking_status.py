"""Thinking status messages for graph nodes.

Reusable mapping of node names to user-facing status text.
Used by the voice handler to stream thinking indicators to the frontend.
"""

NODE_THINKING: dict[str, str] = {
    "bsga": "processing...",
    "moa": "checking information...",
    "tool_planner": "checking information...",
    "db_oracle": "checking information...",
    "db_translator": "preparing response...",
    "domain_router": "checking information...",
    "onboarding": "thinking...",
    "transactions": "thinking...",
    "inventory": "thinking...",
    "response": "",
}


def get_thinking_status(node_name: str) -> str:
    """Get the thinking status message for a node.

    Args:
        node_name: The graph node name.

    Returns:
        User-facing status text, or "thinking..." as default.
    """
    return NODE_THINKING.get(node_name, "thinking...")
