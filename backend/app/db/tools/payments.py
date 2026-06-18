"""Payment database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("record_payment")
async def record_payment(
    business_id: str,
    amount: float,
    customer_id: str = "",
    invoice_id: str = "",
    payment_method: str = "cash",
    reference: str = "",
    **kwargs,
) -> dict:
    """Record a payment received."""
    client = get_client()
    data = {
        "business_id": business_id,
        "amount": amount,
        "payment_method": payment_method,
        "reference": reference,
    }
    if customer_id:
        data["customer_id"] = customer_id
    if invoice_id:
        data["invoice_id"] = invoice_id

    result = client.table("payments").insert(data).execute()
    return result.data[0] if result.data else data


@register("get_payments")
async def get_payments(business_id: str, customer_id: str = "", limit: int = 20, **kwargs) -> dict:
    """Get recent payments."""
    client = get_client()
    q = client.table("payments").select("*, customers(name)").eq("business_id", business_id)
    if customer_id:
        q = q.eq("customer_id", customer_id)
    result = q.order("created_at", desc=True).limit(limit).execute()
    return {"results": result.data or [], "count": len(result.data or [])}
