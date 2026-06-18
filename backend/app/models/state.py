"""Graph state definition."""

import operator
from typing import Annotated, Literal, TypedDict


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
    confirmation_status: Literal["pending", "confirmed", "rejected", "timeout"] | None
    output_mode: Literal["conversation", "structured_options"] | None
    response: dict | None
    messages: Annotated[list[dict], operator.add]
    error: str | None
