"""Transaction tools — business_id pre-baked via closure."""

import json
from langchain_core.tools import tool


def get_transaction_tools(business_id: str) -> list:

    @tool
    async def fetch_transactions(limit: int = 10, transaction_type: str = "", status: str = "") -> dict:
        """Fetch recent transactions. Filter by type or status optionally."""
        from app.db.tools.transactions import get_transactions
        result = await get_transactions(business_id, limit=limit, transaction_type=transaction_type, status=status)
        if not result:
            return {"content": "No results.", "metadata": {}, "images": [], "videos": [], "audios": []}
        return {"content": json.dumps(result, default=str), "metadata": {"count": len(result)}, "images": [], "videos": [], "audios": []}

    @tool
    async def fetch_transactions_summary(transaction_type: str = "") -> dict:
        """Get a summary of transactions (total revenue, count, completed)."""
        from app.db.tools.transactions import get_transactions_summary
        result = await get_transactions_summary(business_id, transaction_type=transaction_type)
        if not result:
            return {"content": "No results.", "metadata": {}, "images": [], "videos": [], "audios": []}
        return {"content": json.dumps(result, default=str), "metadata": result, "images": [], "videos": [], "audios": []}

    @tool
    async def fetch_customers(query: str = "") -> dict:
        """Search customers by name, phone, or email."""
        from app.db.tools.customers import search_customers
        result = await search_customers(business_id, query=query)
        if not result:
            return {"content": "No results.", "metadata": {}, "images": [], "videos": [], "audios": []}
        return {"content": json.dumps(result, default=str), "metadata": {"count": len(result)}, "images": [], "videos": [], "audios": []}

    @tool
    async def fetch_products(query: str = "") -> dict:
        """Search products by name."""
        from app.db.tools.products import search_products
        result = await search_products(business_id, query=query)
        if not result:
            return {"content": "No results.", "metadata": {}, "images": [], "videos": [], "audios": []}
        return {"content": json.dumps(result, default=str), "metadata": {"count": len(result)}, "images": [], "videos": [], "audios": []}

    return [fetch_transactions, fetch_transactions_summary, fetch_customers, fetch_products]
