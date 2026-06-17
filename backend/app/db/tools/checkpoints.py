"""Operation checkpoint tools."""

from app.db.registry import register


@register("create_checkpoint")
def create_checkpoint(
    business_id: str,
    session_id: str,
    message_id: str,
    operation_type: str,
    user_input: str,
    ai_understanding_summary: str,
    before_state: dict,
    after_state: dict,
) -> dict:
    """Create an operation checkpoint recording before/after state."""
    # TODO: implement via app.db.client
    return {"status": "created"}


@register("get_checkpoints")
def get_checkpoints(business_id: str, session_id: str = "", time_range: dict | None = None) -> dict:
    """Retrieve operation checkpoints for a session or business."""
    # TODO: implement
    return {"checkpoints": []}
