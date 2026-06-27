"""Graph state definition."""

import operator
from collections.abc import Callable
from typing import Annotated, Any, Literal, TypedDict


class GraphState(TypedDict, total=False):
    event: dict
    user_id: str | None
    thread_id: str | None
    business_id: str | None
    classification: str | None
    business_context: dict | None
    session_context: dict | None
    memory_context: str | None
    intent: str | None
    routed_domain: str | None
    tool_requests: list[dict] | None
    domain_result: dict | None
    db_result: dict | None
    output_mode: Literal["conversation"] | None
    response: dict | None
    messages: Annotated[list[dict], operator.add]
    error: str | None
    # Call-stack architecture fields
    current_agent: str | None
    workflow_owner: str | None
    return_to: str | None
    # Pending question from agent (set when waiting_for_user, cleared on next turn)
    pending_question: str | None
    # Thinking callback for streaming thinking to frontend
    thinking_callback: Any
