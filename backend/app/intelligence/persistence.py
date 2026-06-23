"""Persistence layer — translates KnowledgeChangeSets into graph transactions."""

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.graph_client import GraphClient

from app.intelligence.models import (
    KnowledgeChangeSet,
    NodePayload,
    Operation,
    PersistenceError,
    PersistenceResult,
)

logger = logging.getLogger(__name__)


def _flatten_props(properties: dict) -> dict:
    """Flatten nested dicts/lists to JSON strings for graph storage compatibility."""
    flat = {}
    for key, value in properties.items():
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, default=str)
        elif value is None:
            flat[key] = ""
        else:
            flat[key] = value
    return flat


def _cypher_for_operation(op: Operation) -> tuple[str, dict]:
    """Generate Cypher query for a single operation."""
    action = op.action

    if action == "create_entity" and op.entity:
        entity = op.entity
        flat_props = _flatten_props(entity.properties)
        props = {
            **flat_props,
            "entity_id": entity.id,
            "_type": entity.type,
            "_payload": json.dumps(entity.properties, default=str),
            "_confidence": op.confidence,
            "_change_type": op.change_type,
        }
        label = entity.type.replace(" ", "_")
        query = f"CREATE (n:{label} $props) RETURN n.entity_id AS entity_id"
        return query, {"props": props}

    elif action == "update_entity" and op.entity:
        entity = op.entity
        flat_props = _flatten_props(entity.properties)
        props = {
            **flat_props,
            "_payload": json.dumps(entity.properties, default=str),
            "_confidence": op.confidence,
            "_change_type": op.change_type,
        }
        query = "MATCH (n {entity_id: $entity_id}) SET n += $props RETURN n.entity_id AS entity_id"
        return query, {"entity_id": entity.id, "props": props}

    elif action == "merge_entity" and op.entity:
        # Merge: copy props from source to target, archive source
        entity = op.entity
        source_id = entity.properties.get("source_entity_id", entity.id)
        target_id = entity.properties.get("target_entity_id", "")
        query = (
            "MATCH (src {entity_id: $source_id}), (tgt {entity_id: $target_id}) "
            "SET tgt += properties(src), tgt._merge_confidence = $confidence "
            "SET src._archived = true, src._merged_into = $target_id "
            "RETURN tgt.entity_id AS entity_id"
        )
        return query, {"source_id": source_id, "target_id": target_id, "confidence": op.confidence}

    elif action == "archive_entity" and op.entity:
        entity = op.entity
        query = (
            "MATCH (n {entity_id: $entity_id}) "
            "SET n._archived = true, n._change_type = $change_type "
            "RETURN n.entity_id AS entity_id"
        )
        return query, {"entity_id": entity.id, "change_type": op.change_type}

    elif action == "create_relationship" and op.relationship:
        rel = op.relationship
        rel_type = rel.relationship_type.replace(" ", "_").upper()
        props = {**_flatten_props(rel.properties), "_confidence": op.confidence, "_change_type": op.change_type}
        query = (
            f"MATCH (a {{entity_id: $source_id}}), (b {{entity_id: $target_id}}) "
            f"CREATE (a)-[r:{rel_type} $props]->(b) "
            f"RETURN type(r) AS type"
        )
        return query, {"source_id": rel.source_entity_id, "target_id": rel.target_entity_id, "props": props}

    elif action == "update_relationship" and op.relationship:
        rel = op.relationship
        rel_type = rel.relationship_type.replace(" ", "_").upper()
        props = {**_flatten_props(rel.properties), "_confidence": op.confidence}
        query = (
            f"MATCH (a {{entity_id: $source_id}})-[r:{rel_type}]->(b {{entity_id: $target_id}}) "
            f"SET r += $props RETURN type(r) AS type"
        )
        return query, {"source_id": rel.source_entity_id, "target_id": rel.target_entity_id, "props": props}

    elif action == "remove_relationship" and op.relationship:
        rel = op.relationship
        rel_type = rel.relationship_type.replace(" ", "_").upper()
        query = (
            f"MATCH (a {{entity_id: $source_id}})-[r:{rel_type}]->(b {{entity_id: $target_id}}) "
            f"DELETE r RETURN $source_id AS source_id"
        )
        return query, {"source_id": rel.source_entity_id, "target_id": rel.target_entity_id}

    else:
        raise PersistenceError(f"Unknown action or missing data: {action}", failed_operation=op)


class PersistenceLayer:
    """Translates KnowledgeChangeSets into atomic graph transactions."""

    def __init__(self, graph_client: "GraphClient"):
        self._graph = graph_client

    async def persist(self, change_set: KnowledgeChangeSet) -> PersistenceResult:
        """Apply all operations atomically in a single transaction."""
        if not change_set.operations:
            return PersistenceResult(
                success=True, operations_applied=0,
                nodes_created=0, nodes_updated=0, relationships_created=0,
            )

        queries: list[tuple[str, dict]] = []
        nodes_created = 0
        nodes_updated = 0
        relationships_created = 0
        affected_nodes: list[NodePayload] = []

        for op in change_set.operations:
            query, params = _cypher_for_operation(op)
            queries.append((query, params))

            if op.action == "create_entity" and op.entity:
                nodes_created += 1
                affected_nodes.append(NodePayload(entity_id=op.entity.id, payload=op.entity.properties))
            elif op.action in ("update_entity", "merge_entity") and op.entity:
                nodes_updated += 1
                affected_nodes.append(NodePayload(entity_id=op.entity.id, payload=op.entity.properties))
            elif op.action in ("create_relationship", "update_relationship"):
                relationships_created += 1

        try:
            await self._graph.execute_write(queries)
        except Exception as e:
            raise PersistenceError(f"Graph transaction failed: {e}") from e

        # Generate embeddings for affected nodes
        embedding_results = []
        if affected_nodes:
            try:
                from app.embeddings.client import get_embedding_client
                embedder = get_embedding_client()
                texts = [json.dumps(n.payload, default=str) for n in affected_nodes]
                embeddings = await embedder.aembed_documents(texts)

                embed_queries = []
                for node, embedding in zip(affected_nodes, embeddings):
                    embed_queries.append((
                        "MATCH (n {entity_id: $entity_id}) SET n._embedding = $embedding",
                        {"entity_id": node.entity_id, "embedding": embedding},
                    ))
                await self._graph.execute_write(embed_queries)
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")

        return PersistenceResult(
            success=True,
            operations_applied=len(change_set.operations),
            nodes_created=nodes_created,
            nodes_updated=nodes_updated,
            relationships_created=relationships_created,
            embedding_results=embedding_results,
        )
