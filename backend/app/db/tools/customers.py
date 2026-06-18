"""Customer database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("search_customers")
async def search_customers(business_id: str, query: str = "", **kwargs) -> dict:
    """Search customers by name, phone, or email."""
    client = get_client()
    q = client.table("customers").select("*").eq("business_id", business_id)
    if query:
        q = q.or_(f"name.ilike.%{query}%,phone.ilike.%{query}%,email.ilike.%{query}%")
    result = q.limit(20).execute()
    return {"results": result.data or [], "count": len(result.data or [])}


@register("create_customer")
async def create_customer(
    business_id: str, name: str, phone: str = "", email: str = "", customer_type: str = "customer", **kwargs
) -> dict:
    """Create a new customer."""
    client = get_client()
    data = {
        "business_id": business_id,
        "name": name,
        "phone": phone,
        "email": email,
        "type": customer_type,
    }
    result = client.table("customers").insert(data).execute()
    return result.data[0] if result.data else data


@register("get_customer")
async def get_customer(business_id: str, customer_id: str, **kwargs) -> dict:
    """Get a customer by ID."""
    client = get_client()
    result = (
        client.table("customers")
        .select("*")
        .eq("id", customer_id)
        .eq("business_id", business_id)
        .single()
        .execute()
    )
    return result.data if result.data else {"error": "Not found"}


@register("update_customer")
async def update_customer(business_id: str, customer_id: str, **kwargs) -> dict:
    """Update a customer."""
    client = get_client()
    updates = {k: v for k, v in kwargs.items() if k in ("name", "phone", "email", "type", "balance")}
    if not updates:
        return {"error": "No valid fields to update"}
    result = (
        client.table("customers")
        .update(updates)
        .eq("id", customer_id)
        .eq("business_id", business_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "Update failed"}
