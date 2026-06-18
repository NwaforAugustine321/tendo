"""Product database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("search_products")
async def search_products(business_id: str, query: str = "", **kwargs) -> dict:
    """Search products by name or category."""
    client = get_client()
    q = client.table("products").select("*").eq("business_id", business_id)
    if query:
        q = q.ilike("name", f"%{query}%")
    result = q.limit(20).execute()
    return {"results": result.data or [], "count": len(result.data or [])}


@register("create_product")
async def create_product(
    business_id: str, name: str, unit_price: float = 0, unit: str = "", category: str = "", **kwargs
) -> dict:
    """Create a new product."""
    client = get_client()
    data = {
        "business_id": business_id,
        "name": name,
        "unit_price": unit_price,
        "unit": unit,
        "category": category,
    }
    result = client.table("products").insert(data).execute()
    return result.data[0] if result.data else data


@register("update_product")
async def update_product(business_id: str, product_id: str, **kwargs) -> dict:
    """Update a product."""
    client = get_client()
    updates = {k: v for k, v in kwargs.items() if k in ("name", "unit_price", "unit", "category")}
    if not updates:
        return {"error": "No valid fields to update"}
    result = (
        client.table("products")
        .update(updates)
        .eq("id", product_id)
        .eq("business_id", business_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "Update failed"}


@register("delete_product")
async def delete_product(business_id: str, product_id: str, **kwargs) -> dict:
    """Delete a product."""
    client = get_client()
    result = (
        client.table("products")
        .delete()
        .eq("id", product_id)
        .eq("business_id", business_id)
        .execute()
    )
    return {"deleted": True} if result.data else {"error": "Delete failed"}
