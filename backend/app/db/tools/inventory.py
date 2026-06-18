"""Inventory database operations."""

import logging

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("get_inventory")
async def get_inventory(business_id: str, product_id: str = "", **kwargs) -> dict:
    """Get inventory items, optionally filtered by product."""
    client = get_client()
    q = client.table("inventory").select("*, products(name, unit_price)").eq("business_id", business_id)
    if product_id:
        q = q.eq("product_id", product_id)
    result = q.limit(50).execute()
    return {"results": result.data or [], "count": len(result.data or [])}


@register("update_inventory")
async def update_inventory(business_id: str, inventory_id: str, quantity: float, **kwargs) -> dict:
    """Update inventory quantity."""
    client = get_client()
    result = (
        client.table("inventory")
        .update({"quantity": quantity})
        .eq("id", inventory_id)
        .eq("business_id", business_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "Update failed"}


@register("add_inventory")
async def add_inventory(business_id: str, product_id: str, quantity: float = 0, reorder_level: float = 0, **kwargs) -> dict:
    """Add a new inventory entry for a product."""
    client = get_client()
    data = {
        "business_id": business_id,
        "product_id": product_id,
        "quantity": quantity,
        "reorder_level": reorder_level,
    }
    result = client.table("inventory").insert(data).execute()
    return result.data[0] if result.data else data


@register("record_inventory_movement")
async def record_inventory_movement(
    business_id: str, inventory_id: str, movement_type: str, quantity: float, reference: str = "", **kwargs
) -> dict:
    """Record an inventory movement (in/out/adjustment)."""
    client = get_client()
    data = {
        "business_id": business_id,
        "inventory_id": inventory_id,
        "movement_type": movement_type,
        "quantity": quantity,
        "reference": reference,
    }
    result = client.table("inventory_movements").insert(data).execute()

    # Also update the inventory quantity
    inv = client.table("inventory").select("quantity").eq("id", inventory_id).single().execute()
    if inv.data:
        current = float(inv.data["quantity"])
        new_qty = current + quantity if movement_type == "in" else current - quantity
        client.table("inventory").update({"quantity": new_qty}).eq("id", inventory_id).execute()

    return result.data[0] if result.data else data
