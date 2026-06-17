"""Graph state definition."""

from typing import Literal, TypedDict


class GraphState(TypedDict, total=False):
    event: dict
    classification: str | None
    business_context: dict | None
    session_context: dict | None
    intent: str | None
    routed_domain: str | None
    tool_requests: list[dict] | None
    domain_result: dict | None
    db_result: dict | None
    confirmation_status: Literal["pending", "confirmed", "rejected", "timeout"] | None
    output_mode: Literal["conversation", "structured_options"] | None
    response: dict | None
    messages: list[dict]
    error: str | None
