"""LangChain tool wrappers for transaction DB operations.

These are the @tool-decorated functions that the transactions agent uses directly.
They wrap the plain functions in app/db/tools/transactions.py, customers.py, products.py.
"""

import json

from langchain_core.tools import tool


@tool
async def fetch_transactions(business_id: str, limit: int = 10, transaction_type: str = "", status: str = "") -> str:
    """Fetch recent transactions for a business. Filter by type or status optionally."""
    from app.db.tools.transactions import get_transactions
    result = await get_transactions(business_id, limit=limit, transaction_type=transaction_type, status=status)
    return json.dumps(result, default=str)


@tool
async def fetch_transactions_summary(business_id: str, transaction_type: str = "") -> str:
    """Get a summary of transactions (total revenue, count, completed)."""
    from app.db.tools.transactions import get_transactions_summary
    result = await get_transactions_summary(business_id, transaction_type=transaction_type)
    return json.dumps(result, default=str)


@tool
async def fetch_customers(business_id: str, query: str = "") -> str:
    """Search customers by name, phone, or email."""
    from app.db.tools.customers import search_customers
    result = await search_customers(business_id, query=query)
    return json.dumps(result, default=str)


@tool
async def fetch_products(business_id: str, query: str = "") -> str:
    """Search products by name."""
    from app.db.tools.products import search_products
    result = await search_products(business_id, query=query)
    return json.dumps(result, default=str)


TRANSACTION_TOOLS = [fetch_transactions, fetch_transactions_summary, fetch_customers, fetch_products]
