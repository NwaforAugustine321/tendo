"""Sales tools."""

from app.db.registry import register


@register("create_sale")
def create_sale(
    business_id: str,
    customer_id: str,
    items: list[dict],
    payment_type: str,
    event_id: str,
    confirmation_status: str = "",
) -> dict:
    """Create a sale transaction. Requires confirmation."""
    if confirmation_status != "confirmed":
        return {"error": "Confirmation required before executing write operation."}
    # TODO: idempotency check, execute, audit log
    return {"status": "created", "event_id": event_id}
