"""Service tools."""

from app.db.registry import register


@register("search_services")
def search_services(business_id: str, query: str = "") -> dict:
    """Search services."""
    # TODO: implement via app.db.client
    return {"results": [], "query": query}
