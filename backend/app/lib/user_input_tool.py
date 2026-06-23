"""User input tool — allows specialist agents to ask questions to the user.

When called, returns a __WAITING__ signal that short-circuits the executor,
causing the node to send the question/fields to the frontend.
The graph checkpointer handles resumption when the user responds.
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class AskUserQuestionInput(BaseModel):
    """Input schema for the ask_user_question tool."""

    question: str = Field(..., description="The question to ask the user (spoken via TTS)")
    fields: str = Field(
        default="[]",
        description=(
            'JSON array of input fields to collect from the user. '
            'Each field MUST have: "id", "name", "label", "description". '
            'All choices for the same question share the same "name". '
            'Example: [{"id": "cash", "name": "payment_type", "label": "Cash", "description": "Customer paid with cash"}, '
            '{"id": "transfer", "name": "payment_type", "label": "Transfer", "description": "Customer paid via bank transfer"}, '
            '{"id": "other", "name": "payment_type", "label": "Other", "description": "Another payment method"}]'
        ),
    )


def _ask_user_question(question: str, fields: str = "[]") -> str:
    """Ask the user a question with structured input fields.

    Returns a __WAITING__ signal that the executor detects and returns immediately.
    The node then parses this into a waiting_for_user response with fields.
    """
    try:
        parsed_fields = json.loads(fields) if fields else []
    except json.JSONDecodeError:
        parsed_fields = []

    payload = {
        "response": question,
        "workflow_status": "waiting_for_user",
        "workflow_state": "awaiting_user_input",
        "authoritative": True,
        "fields": parsed_fields,
    }
    return f"__WAITING__|{json.dumps(payload)}"


# The tool instance — add to any specialist agent's tools list
ask_user_question = StructuredTool.from_function(
    func=_ask_user_question,
    name="ask_user_question",
    description=(
        "Ask the user a question and collect their choice. "
        "Use this when you need information from the user before continuing. "
        "Provide the question text (spoken aloud via TTS) and a JSON array of choice fields. "
        "Each field must have: id, name, label, description. "
        "All choices for the same question share the same name value."
    ),
    args_schema=AskUserQuestionInput,
)
