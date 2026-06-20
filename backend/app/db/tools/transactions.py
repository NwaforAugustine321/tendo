"""Transaction database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("record_transaction")
async def record_transaction(
    business_id: str,
    total: float,
    transaction_type: str = "",
    payment_type: str = "",
    status: str = "",
    narration: str = "",
    customer_id: str = "",
    items: list = None,
    **kwargs,
) -> dict:
    """Record a transaction with type, payment, total, status, narration, and optional metadata."""
    client = get_client()
    data = {
        "business_id": business_id,
        "type": transaction_type,
        "total": total,
        "payment_type": payment_type,
        "status": status,
        "metadata": {"items": items or [], "narration": narration, **kwargs.get("metadata", {})},
    }
    if customer_id:
        data["customer_id"] = customer_id

    result = client.table("transactions").insert(data).execute()
    return result.data[0] if result.data else data


@register("get_transactions")
async def get_transactions(business_id: str, limit: int = 10, offset: int = 0, status: str = "", transaction_type: str = "", **kwargs) -> dict:
    """Get transactions with pagination. Filter by type or status optionally."""
    client = get_client()
    q = client.table("transactions").select("*, customers(name)").eq("business_id", business_id)
    if transaction_type:
        q = q.eq("type", transaction_type)
    if status:
        q = q.eq("status", status)
    result = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"results": result.data or [], "count": len(result.data or []), "offset": offset, "limit": limit, "has_more": len(result.data or []) == limit}


@register("get_transactions_summary")
async def get_transactions_summary(business_id: str, transaction_type: str = "", **kwargs) -> dict:
    """Get transactions summary (total, count). Optionally filter by type."""
    client = get_client()
    q = client.table("transactions").select("total, status, type").eq("business_id", business_id)
    if transaction_type:
        q = q.eq("type", transaction_type)
    result = q.execute()
    transactions = result.data or []
    total_revenue = sum(float(t["total"]) for t in transactions if t["status"] == "completed")
    return {
        "total_revenue": total_revenue,
        "total_transactions": len(transactions),
        "completed": len([t for t in transactions if t["status"] == "completed"]),
    }


@register("update_transaction")
async def update_transaction(business_id: str, transaction_id: str, **kwargs) -> dict:
    """Update a transaction."""
    client = get_client()
    valid_fields = ("total", "payment_type", "status", "customer_id", "metadata", "type")
    updates = {k: v for k, v in kwargs.items() if k in valid_fields and v}
    if not updates:
        return {"error": "No valid fields to update"}
    result = (
        client.table("transactions")
        .update(updates)
        .eq("id", transaction_id)
        .eq("business_id", business_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "Update failed"}


@register("delete_transaction")
async def delete_transaction(business_id: str, transaction_id: str, **kwargs) -> dict:
    """Delete a transaction."""
    client = get_client()
    result = (
        client.table("transactions")
        .delete()
        .eq("id", transaction_id)
        .eq("business_id", business_id)
        .execute()
    )
    return {"deleted": True} if result.data else {"error": "Delete failed"}
