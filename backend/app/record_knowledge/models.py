from typing import Any

from pydantic import BaseModel, Field


class KnowledgeEntry(BaseModel):
    knowledge_id: str
    business_id: str
    record_id: str
    content_type: str
    summary: str
    structured_metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] = Field(default_factory=list)
    version: int = 1
    created_at: str
    updated_at: str


class RecordContentInput(BaseModel):
    business_id: str
    record_id: str
    content_type: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessingResult(BaseModel):
    success: bool
    entry: KnowledgeEntry | None = None
    error: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)


class AIUnderstanding(BaseModel):
    insight: str = ""
    suggested_questions: list[str] = Field(default_factory=list)


class ProcessingStatus(BaseModel):
    status: str
    record_id: str
    error: str | None = None
    summary: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)


class CreateFolderRequest(BaseModel):
    business_id: str
    name: str
    icon: str = ""
    color: str = ""


class CreateRecordRequest(BaseModel):
    business_id: str
    folder_id: str = ""
    title: str


class UpdateRecordRequest(BaseModel):
    business_id: str
    title: str = ""
    folder_id: str = ""


class AddContentRequest(BaseModel):
    business_id: str
    content_type: str = "text"
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
