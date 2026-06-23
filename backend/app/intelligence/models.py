"""Pydantic models for the Business Intelligence Agent."""

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Change Types (controlled vocabulary)
# ---------------------------------------------------------------------------

VALID_CHANGE_TYPES = [
    # Entity
    "EntityCreated", "EntityUpdated", "EntityMerged", "EntityArchived", "EntityDeleted",
    # Employee
    "EmployeeCreated", "EmployeeUpdated", "EmployeeRoleChanged",
    "EmployeeTransferred", "EmployeeTerminated", "EmployeeManagerChanged",
    # Customer
    "CustomerCreated", "CustomerUpdated", "CustomerMerged", "CustomerStatusChanged",
    # Workflow
    "WorkflowCreated", "WorkflowUpdated", "WorkflowArchived",
    "WorkflowAssignedToDepartment", "WorkflowOwnershipChanged",
    # Project
    "ProjectCreated", "ProjectUpdated", "ProjectArchived",
    "ProjectStatusChanged", "ProjectOwnershipChanged",
    # Product
    "ProductCreated", "ProductUpdated", "ProductDiscontinued", "InventoryThresholdChanged",
    # Policy
    "PolicyCreated", "PolicyUpdated", "PolicyArchived",
    # Business
    "BusinessProfileUpdated", "BusinessRuleCreated", "BusinessRuleUpdated",
    "TerminologyCreated", "TerminologyUpdated",
    # Relationship
    "RelationshipCreated", "RelationshipUpdated", "RelationshipRemoved",
]


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    NEEDS_RETRIEVAL = "needs_retrieval"
    NO_CHANGES = "no_changes"


# ---------------------------------------------------------------------------
# Operation Models (new format)
# ---------------------------------------------------------------------------


class EntityPayload(BaseModel):
    """Entity data for create/update operations."""
    id: str
    type: str
    properties: dict = Field(default_factory=dict)


class RelationshipPayload(BaseModel):
    """Relationship data for relationship operations."""
    source_entity_id: str
    relationship_type: str
    target_entity_id: str
    properties: dict = Field(default_factory=dict)


class OperationMetadata(BaseModel):
    """Metadata about an operation."""
    created_from: str = "business_events"
    business_domain: str = ""
    priority: str = "normal"


class Operation(BaseModel):
    """A single knowledge change operation."""
    operation_id: str = Field(default_factory=lambda: f"op_{uuid4().hex[:6]}")
    action: str  # create_entity, update_entity, merge_entity, archive_entity, create_relationship, update_relationship, remove_relationship
    change_type: str  # From VALID_CHANGE_TYPES
    entity: EntityPayload | None = None
    relationship: RelationshipPayload | None = None
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    evidence: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool Request (for needs_retrieval status)
# ---------------------------------------------------------------------------


class ToolRequest(BaseModel):
    """A tool retrieval request."""
    tool: str
    params: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Knowledge Change Set (top-level output)
# ---------------------------------------------------------------------------


class KnowledgeChangeSet(BaseModel):
    """The agent's complete output."""
    reasoning_summary: str = ""
    status: AgentStatus = AgentStatus.COMPLETED
    tool_requests: list[ToolRequest] = Field(default_factory=list)
    operations: list[Operation] = Field(default_factory=list)
    business_id: str = ""
    job_id: str = ""


# ---------------------------------------------------------------------------
# Persistence Models
# ---------------------------------------------------------------------------


class EmbeddingResult(BaseModel):
    entity_id: str
    success: bool
    error: str | None = None


class PersistenceResult(BaseModel):
    """Result of applying a KnowledgeChangeSet to the graph."""
    success: bool
    operations_applied: int
    nodes_created: int
    nodes_updated: int
    relationships_created: int
    embedding_results: list[EmbeddingResult] = Field(default_factory=list)


class NodePayload(BaseModel):
    """Payload for embedding generation."""
    entity_id: str
    payload: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class IntelligenceError(Exception):
    """Base exception for the intelligence module."""
    pass


class AgentError(IntelligenceError):
    """Raised when the agent reasoning loop fails."""
    def __init__(self, message: str, iteration: int = 0, partial_understanding: str = ""):
        self.iteration = iteration
        self.partial_understanding = partial_understanding
        super().__init__(message)


class PersistenceError(IntelligenceError):
    """Raised when graph persistence fails."""
    def __init__(self, message: str, failed_operation=None):
        self.failed_operation = failed_operation
        super().__init__(message)


class ExecutionError(IntelligenceError):
    """Raised for execution layer failures."""
    pass
