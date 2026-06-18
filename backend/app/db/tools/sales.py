"""Sales/transaction database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("record_sale")
async def record_sale(
    business_id: str,
    total: float,
    customer_id: str = "",
    payment_type: str = "cash",
    items: list = None,
    **kwargs,
) -> dict:
    """Record a sale transaction."""
    client = get_client()
    data = {
        "business_id": business_id,
        "type": "sale",
        "total": total,
        "payment_type": payment_type,
        "status": "completed",
        "metadata": {"items": items or []},
    }
    if customer_id:
        data["customer_id"] = customer_id

    result = client.table("transactions").insert(data).execute()
    return result.data[0] if result.data else data


@register("get_sales")
async def get_sales(business_id: str, limit: int = 20, status: str = "", **kwargs) -> dict:
    """Get recent sales."""
    client = get_client()
    q = client.table("transactions").select("*, customers(name)").eq("business_id", business_id).eq("type", "sale")
    if status:
        q = q.eq("status", status)
    result = q.order("created_at", desc=True).limit(limit).execute()
    return {"results": result.data or [], "count": len(result.data or [])}


@register("get_sales_summary")
async def get_sales_summary(business_id: str, **kwargs) -> dict:
    """Get sales summary (total, count)."""
    client = get_client()
    result = (
        client.table("transactions")
        .select("total, status")
        .eq("business_id", business_id)
        .eq("type", "sale")
        .execute()
    )
    transactions = result.data or []
    total_revenue = sum(float(t["total"]) for t in transactions if t["status"] == "completed")
    return {
        "total_revenue": total_revenue,
        "total_transactions": len(transactions),
        "completed": len([t for t in transactions if t["status"] == "completed"]),
    }
