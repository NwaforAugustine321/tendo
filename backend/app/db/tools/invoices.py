"""Invoice tools."""

from app.db.registry import register


@register("search_invoices")
def search_invoices(business_id: str, customer_id: str = "", status: str = "") -> dict:
    """Search invoices."""
    # TODO: implement via app.db.client
    return {"results": []}
