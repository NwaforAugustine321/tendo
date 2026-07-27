"""Pydantic models for ExecutionContext and SharedContext."""

from pydantic import BaseModel, Field


class Constraint(BaseModel):
    name: str
    condition: str


class ToolReference(BaseModel):
    tool_id: str
    capability: str


class SkillEntry(BaseModel):
    skill_id: str
    category: str
    content: str


class KnowledgeEntry(BaseModel):
    collection_id: str
    domain: str
    content: str


class OutputSpec(BaseModel):
    format: str
    schema_ref: str | None = None
    required_fields: list[str] = Field(default_factory=list)


class ExecutionContext(BaseModel):
    objective: str = Field(min_length=1)
    skills: list[SkillEntry] = Field(default_factory=list)
    knowledge: list[KnowledgeEntry] = Field(default_factory=list)
    available_tools: list[ToolReference] = Field(default_factory=list)
    expected_output: OutputSpec
    constraints: list[Constraint] = Field(default_factory=list)


class SharedContext(BaseModel):
    user_request: str
    uploaded_files: list[str] = Field(default_factory=list)
    conversation_messages: list[dict] = Field(default_factory=list)
    business_id: str
    shared_constraints: list[Constraint] = Field(default_factory=list)
