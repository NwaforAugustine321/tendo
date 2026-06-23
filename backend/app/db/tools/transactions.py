"""Transaction database operations with event emission."""

import logging

from app.db.client import get_client
from app.events.writer import EventWriter

logger = logging.getLogger(__name__)

_event_writer = EventWriter()


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
    """Record a transaction."""
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
    transaction = result.data[0] if result.data else data

    if result.data:
        _event_writer.write(
            business_id=business_id,
            entity_type="transaction",
            entity_id=transaction.get("id", ""),
            event_type="TransactionCreated",
            source="system",
            payload={"total": total, "type": transaction_type, "payment_type": payment_type, "status": status},
            metadata={"customer_id": customer_id, "narration": narration},
        )

    return transaction


async def get_transactions(business_id: str, limit: int = 10, offset: int = 0, status: str = "", transaction_type: str = "", **kwargs) -> dict:
    """Get transactions with pagination."""
    client = get_client()
    q = client.table("transactions").select("*, customers(name)").eq("business_id", business_id)
    if transaction_type:
        q = q.eq("type", transaction_type)
    if status:
        q = q.eq("status", status)
    result = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"results": result.data or [], "count": len(result.data or []), "offset": offset, "limit": limit, "has_more": len(result.data or []) == limit}


async def get_transactions_summary(business_id: str, transaction_type: str = "", **kwargs) -> dict:
    """Get transactions summary."""
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

    if result.data:
        _event_writer.write(
            business_id=business_id,
            entity_type="transaction",
            entity_id=transaction_id,
            event_type="TransactionUpdated",
            source="system",
            payload=updates,
            metadata={"transaction_id": transaction_id},
        )

    return result.data[0] if result.data else {"error": "Update failed"}


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

    if result.data:
        _event_writer.write(
            business_id=business_id,
            entity_type="transaction",
            entity_id=transaction_id,
            event_type="TransactionDeleted",
            source="system",
            payload={"transaction_id": transaction_id},
            metadata={},
        )

    return {"deleted": True} if result.data else {"error": "Delete failed"}
