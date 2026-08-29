"""Invoice database operations."""

import logging

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def create_invoice(
    business_id: str,
    customer_id: str,
    total: float,
    due_date: str = "",
    items: list = None,
    **kwargs,
) -> dict:
    """Create an invoice."""
    client = get_client()
    data = {
        "business_id": business_id,
        "customer_id": customer_id,
        "total": total,
        "status": "pending",
    }
    if due_date:
        data["due_date"] = due_date

    result = client.table("invoices").insert(data).execute()
    invoice = result.data[0] if result.data else data

    # Add line items if provided
    if items and invoice.get("id"):
        for item in items:
            line = {
                "business_id": business_id,
                "invoice_id": invoice["id"],
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price", 0),
                "total": item.get("quantity", 1) * item.get("unit_price", 0),
            }
            client.table("invoice_line_items").insert(line).execute()

    return invoice


async def get_invoices(business_id: str, status: str = "", customer_id: str = "", limit: int = 20, **kwargs) -> dict:
    """Get invoices."""
    client = get_client()
    q = client.table("invoices").select("*, customers(name)").eq("business_id", business_id)
    if status:
        q = q.eq("status", status)
    if customer_id:
        q = q.eq("customer_id", customer_id)
    result = q.order("created_at", desc=True).limit(limit).execute()
    return {"results": result.data or [], "count": len(result.data or [])}


async def update_invoice_status(business_id: str, invoice_id: str, status: str, **kwargs) -> dict:
    """Update invoice status (pending, paid, overdue, cancelled)."""
    client = get_client()
    result = (
        client.table("invoices")
        .update({"status": status})
        .eq("id", invoice_id)
        .eq("business_id", business_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "Update failed"}
