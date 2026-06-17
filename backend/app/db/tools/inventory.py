"""Inventory tools."""

from app.db.registry import register


@register("search_inventory")
def search_inventory(business_id: str, product_id: str = "") -> dict:
    """Search inventory levels."""
    # TODO: implement via app.db.client
    return {"results": []}


@register("update_inventory")
def update_inventory(
    business_id: str,
    product_id: str,
    quantity_change: float,
    movement_type: str,
    event_id: str,
    confirmation_status: str = "",
) -> dict:
    """Update inventory. Requires confirmation."""
    if confirmation_status != "confirmed":
        return {"error": "Confirmation required before executing write operation."}
    # TODO: implement
    return {"status": "updated", "event_id": event_id}
