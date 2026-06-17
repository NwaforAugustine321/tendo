"""Customer search tool."""

from app.db.registry import register


@register("search_customers")
def search_customers(business_id: str, query: str = "") -> dict:
    """Search customers by name or phone."""
    # TODO: implement via app.db.client
    return {"results": [], "query": query}
