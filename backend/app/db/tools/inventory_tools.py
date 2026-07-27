"""Inventory tools — business_id pre-baked via closure."""

import json
from langchain_core.tools import tool


def get_inventory_tools(business_id: str) -> list:

    @tool
    async def fetch_inventory(product_id: str = "") -> str:
        """Fetch inventory items, optionally filtered by product."""
        from app.db.tools.inventory import get_inventory
        result = await get_inventory(business_id, product_id=product_id)
        if not result:
            return "No results."
        return json.dumps(result, default=str)

    @tool
    async def fetch_products(query: str = "") -> str:
        """Search products by name or category."""
        from app.db.tools.products import search_products
        result = await search_products(business_id, query=query)
        if not result:
            return "No results."
        return json.dumps(result, default=str)

    @tool
    async def add_inventory_item(product_id: str, quantity: float = 0, reorder_level: float = 0) -> str:
        """Add a new inventory entry for a product."""
        from app.db.tools.inventory import add_inventory
        result = await add_inventory(business_id, product_id, quantity=quantity, reorder_level=reorder_level)
        if not result:
            return "No results."
        return json.dumps(result, default=str)

    @tool
    async def record_movement(inventory_id: str, movement_type: str, quantity: float, reference: str = "") -> str:
        """Record an inventory movement (in/out/adjustment)."""
        from app.db.tools.inventory import record_inventory_movement
        result = await record_inventory_movement(business_id, inventory_id, movement_type, quantity, reference=reference)
        if not result:
            return "No results."
        return json.dumps(result, default=str)

    @tool
    async def create_product(name: str, unit_price: float = 0, unit: str = "", category: str = "") -> str:
        """Create a new product."""
        from app.db.tools.products import create_product as db_create_product
        result = await db_create_product(business_id, name, unit_price=unit_price, unit=unit, category=category)
        if not result:
            return "No results."
        return json.dumps(result, default=str)

    return [fetch_inventory, fetch_products, add_inventory_item, record_movement, create_product]
