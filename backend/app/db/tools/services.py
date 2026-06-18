"""Service database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("search_services")
async def search_services(business_id: str, query: str = "", **kwargs) -> dict:
    """Search services by name or category."""
    client = get_client()
    q = client.table("services").select("*").eq("business_id", business_id)
    if query:
        q = q.ilike("name", f"%{query}%")
    result = q.limit(20).execute()
    return {"results": result.data or [], "count": len(result.data or [])}


@register("create_service")
async def create_service(
    business_id: str, name: str, price: float = 0, category: str = "", **kwargs
) -> dict:
    """Create a new service."""
    client = get_client()
    data = {
        "business_id": business_id,
        "name": name,
        "price": price,
        "category": category,
    }
    result = client.table("services").insert(data).execute()
    return result.data[0] if result.data else data


@register("update_service")
async def update_service(business_id: str, service_id: str, **kwargs) -> dict:
    """Update a service."""
    client = get_client()
    updates = {k: v for k, v in kwargs.items() if k in ("name", "price", "category")}
    if not updates:
        return {"error": "No valid fields to update"}
    result = (
        client.table("services")
        .update(updates)
        .eq("id", service_id)
        .eq("business_id", business_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "Update failed"}


@register("delete_service")
async def delete_service(business_id: str, service_id: str, **kwargs) -> dict:
    """Delete a service."""
    client = get_client()
    result = (
        client.table("services")
        .delete()
        .eq("id", service_id)
        .eq("business_id", business_id)
        .execute()
    )
    return {"deleted": True} if result.data else {"error": "Delete failed"}
