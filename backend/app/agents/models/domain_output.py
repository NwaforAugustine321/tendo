"""Pydantic models for domain specialist agent output format.

Used by inventory, transactions, and other domain agents.
Passed to build_task_prompt_with_schema as output_pydantic to enforce
structured JSON output via the formatted_task_instructions i18n slice.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TextField(BaseModel):
    """Text input field — user types free text."""

    name: str = Field(description="Field identifier")
    placeholder: str = Field(default="", description="Hint text shown in input")
    description: str = Field(default="", description="Explanation of what to enter")


class ChoiceField(BaseModel):
    """Choice field — user picks one option."""

    id: str = Field(description="Unique option identifier")
    name: str = Field(description="Field name (shared across choices in same group)")
    label: str = Field(description="Display label for this option")
    description: str = Field(default="", description="Explanation of this option")


class ToolRequest(BaseModel):
    """A tool execution request from the agent."""

    tool: str = Field(description="Tool name to execute")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool",
    )


class DomainAgentOutput(BaseModel):
    """Structured output format for domain specialist agents.

    This model enforces the JSON schema that domain agents must return.
    The workflow_status and workflow_state fields control execution flow:
    - completed: task done, no further action
    - waiting_for_user: needs user input (fields required)
    - active: executing tools (tool_requests required)
    - failed: workflow cannot continue
    """

    response: str = Field(
        description="Natural language response spoken aloud via TTS"
    )
    workflow_status: Literal["completed", "waiting_for_user", "active", "failed"] = Field(
        description="Current workflow status"
    )
    workflow_state: Literal[
        "completed",
        "awaiting_user_input",
        "awaiting_confirmation",
        "executing",
        "failed",
    ] = Field(description="Detailed workflow state")
    authoritative: bool = Field(
        default=True,
        description="Whether this agent's output is final (not subject to further reasoning)",
    )
    tool_requests: list[ToolRequest] | None = Field(
        default=None,
        description="Tools to execute (only when workflow_status is 'active')",
    )
    fields: list[TextField | ChoiceField] | None = Field(
        default=None,
        description="Input fields to collect from user (only when workflow_status is 'waiting_for_user')",
    )
    extracted: dict[str, Any] | None = Field(
        default=None,
        description="Information extracted from user so far",
    )
