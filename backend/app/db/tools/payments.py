"""Payment tools."""

from app.db.registry import register


@register("search_payments")
def search_payments(business_id: str, customer_id: str = "", status: str = "") -> dict:
    """Search payments by customer or status."""
    # TODO: implement via app.db.client
    return {"results": []}


@register("create_payment")
def create_payment(
    business_id: str,
    customer_id: str,
    amount: float,
    payment_method: str,
    event_id: str,
    confirmation_status: str = "",
) -> dict:
    """Record a payment. Requires confirmation."""
    if confirmation_status != "confirmed":
        return {"error": "Confirmation required before executing write operation."}
    # TODO: implement
    return {"status": "created", "event_id": event_id}
