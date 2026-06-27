"""LangChain tool wrappers for inventory DB operations.

These are the @tool-decorated functions that agents use directly.
They wrap the plain functions in app/db/tools/inventory.py and products.py.
"""

import json

from langchain_core.tools import tool

from app.memory.knowledge import search_business_knowledge
from app.db.tools.profile_tools import get_business_profile


@tool
async def fetch_inventory(business_id: str, product_id: str = "") -> str:
    """Fetch inventory items, optionally filtered by product."""
    from app.db.tools.inventory import get_inventory
    result = await get_inventory(business_id, product_id=product_id)
    return json.dumps(result, default=str)


@tool
async def fetch_products(business_id: str, query: str = "") -> str:
    """Search products by name or category."""
    from app.db.tools.products import search_products
    result = await search_products(business_id, query=query)
    return json.dumps(result, default=str)


@tool
async def add_inventory_item(business_id: str, product_id: str, quantity: float = 0, reorder_level: float = 0) -> str:
    """Add a new inventory entry for a product."""
    from app.db.tools.inventory import add_inventory
    result = await add_inventory(business_id, product_id, quantity=quantity, reorder_level=reorder_level)
    return json.dumps(result, default=str)


@tool
async def record_movement(business_id: str, inventory_id: str, movement_type: str, quantity: float, reference: str = "") -> str:
    """Record an inventory movement (in/out/adjustment)."""
    from app.db.tools.inventory import record_inventory_movement
    result = await record_inventory_movement(business_id, inventory_id, movement_type, quantity, reference=reference)
    return json.dumps(result, default=str)


@tool
async def create_product(business_id: str, name: str, unit_price: float = 0, unit: str = "", category: str = "") -> str:
    """Create a new product."""
    from app.db.tools.products import create_product as db_create_product
    result = await db_create_product(business_id, name, unit_price=unit_price, unit=unit, category=category)
    return json.dumps(result, default=str)


INVENTORY_TOOLS = [fetch_inventory, fetch_products, add_inventory_item, record_movement, create_product, search_business_knowledge, get_business_profile]
