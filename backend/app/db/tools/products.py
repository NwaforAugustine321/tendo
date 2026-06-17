"""Product search tool."""

from app.db.registry import register


@register("search_products")
def search_products(business_id: str, query: str = "") -> dict:
    """Search products by name or category."""
    # TODO: implement via app.db.client
    return {"results": [], "query": query}
