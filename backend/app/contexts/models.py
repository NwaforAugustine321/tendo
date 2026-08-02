

from pydantic import BaseModel, Field
from typing import Optional


class Constraint(BaseModel):
    name: Optional[str] = None
    condition: Optional[str] = None


class ExecutionContext(BaseModel):
    objective: Optional[str] = Field(default_factory=str)
    skills: list[str] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)
    # available_tools: list[str] = Field(default_factory=list)

class SharedContext(BaseModel):
    user_request: str
    conversation_messages: list[dict] = Field(default_factory=list)
    shared_constraints: str = Field(default_factory=str)
