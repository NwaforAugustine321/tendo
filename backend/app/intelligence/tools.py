"""LangChain tools for Neo4j retrieval (agent uses these via bind_tools)."""

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def query_entities(
    entity_type: str = "", entity_id: str = "", properties: str = ""
) -> str:
    """Query existing entities from the knowledge graph. Filter by entity_type, entity_id, or properties (JSON string)."""
    from app.db.graph_client import get_graph_client

    client = get_graph_client()

    if entity_id:
        query = "MATCH (n {entity_id: $entity_id}) RETURN n LIMIT 10"
        params = {"entity_id": entity_id}
    elif entity_type:
        query = f"MATCH (n:{entity_type}) RETURN n LIMIT 20"
        params = {}
    else:
        query = "MATCH (n) RETURN n LIMIT 20"
        params = {}

    results = await client.execute_read(query, params)
    return json.dumps(results, default=str)


@tool
async def query_relationships(
    source_id: str = "", target_id: str = "", relationship_type: str = ""
) -> str:
    """Query relationships between entities in the knowledge graph."""
    from app.db.graph_client import get_graph_client

    client = get_graph_client()

    if source_id and target_id:
        query = "MATCH (a {entity_id: $source})-[r]->(b {entity_id: $target}) RETURN type(r) as type, properties(r) as props"
        params = {"source": source_id, "target": target_id}
    elif source_id:
        query = "MATCH (a {entity_id: $source})-[r]->(b) RETURN type(r) as type, properties(r) as props, b.entity_id as target LIMIT 20"
        params = {"source": source_id}
    else:
        query = "MATCH (a)-[r]->(b) RETURN a.entity_id as source, type(r) as type, b.entity_id as target LIMIT 20"
        params = {}

    results = await client.execute_read(query, params)
    return json.dumps(results, default=str)


@tool
async def search_similar(text: str, entity_type: str = "", limit: int = 5) -> str:
    """Search for entities with similar content using text matching."""
    from app.db.graph_client import get_graph_client

    client = get_graph_client()

    if entity_type:
        query = f"MATCH (n:{entity_type}) WHERE toLower(n._payload) CONTAINS toLower($text) RETURN n LIMIT $limit"
    else:
        query = "MATCH (n) WHERE toLower(n._payload) CONTAINS toLower($text) RETURN n LIMIT $limit"

    results = await client.execute_read(query, {"text": text, "limit": limit})
    return json.dumps(results, default=str)


@tool
async def get_entity_neighbors(entity_id: str, depth: int = 1) -> str:
    """Get all entities connected to a given entity up to a specified depth."""
    from app.db.graph_client import get_graph_client

    client = get_graph_client()

    safe_depth = min(depth, 3)
    query = f"MATCH (n {{entity_id: $id}})-[r*1..{safe_depth}]-(m) RETURN DISTINCT m.entity_id as entity_id, labels(m) as labels, m._payload as payload LIMIT 30"
    results = await client.execute_read(query, {"id": entity_id})
    return json.dumps(results, default=str)


# All tools available to the intelligence agent
INTELLIGENCE_TOOLS = [query_entities, query_relationships, search_similar, get_entity_neighbors]
