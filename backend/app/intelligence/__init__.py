"""Business Intelligence Agent — public API."""

from app.intelligence.agent import process_events
from app.intelligence.config import IntelligenceConfig, get_intelligence_config
from app.intelligence.models import (
    AgentError,
    AgentStatus,
    EmbeddingResult,
    EntityPayload,
    ExecutionError,
    IntelligenceError,
    KnowledgeChangeSet,
    NodePayload,
    Operation,
    OperationMetadata,
    PersistenceError,
    PersistenceResult,
    RelationshipPayload,
    ToolRequest,
    VALID_CHANGE_TYPES,
)
from app.db.graph_client import GraphClient, get_graph_client
from app.intelligence.persistence import PersistenceLayer
from app.intelligence.tools import INTELLIGENCE_TOOLS

__all__ = [
    "process_events",
    "IntelligenceConfig",
    "get_intelligence_config",
    "AgentStatus",
    "Operation",
    "EntityPayload",
    "RelationshipPayload",
    "OperationMetadata",
    "ToolRequest",
    "VALID_CHANGE_TYPES",
    "KnowledgeChangeSet",
    "PersistenceResult",
    "EmbeddingResult",
    "NodePayload",
    "IntelligenceError",
    "AgentError",
    "PersistenceError",
    "ExecutionError",
    "GraphClient",
    "get_graph_client",
    "PersistenceLayer",
    "INTELLIGENCE_TOOLS",
]
