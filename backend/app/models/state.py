"""LangGraph state definition."""

from typing import Literal, TypedDict


class GraphState(TypedDict, total=False):
    # Event
    event: dict  # UnifiedUserEvent as dict

    # BSGA
    classification: str | None  # IN_SCOPE / OUT_OF_SCOPE

    # Context
    business_context: dict | None  # From BCC
    session_context: dict | None  # From session cache

    # Intent
    intent: str | None
    routed_domain: str | None  # sales / payment / inventory / service

    # Tool planning
    tool_requests: list[dict] | None
    domain_result: dict | None
    db_result: dict | None

    # Confirmation
    confirmation_status: Literal["pending", "confirmed", "rejected", "timeout"] | None

    # Output
    output_mode: Literal["conversation", "structured_options"] | None
    response: dict | None  # ConversationOutput or OptionsOutput

    # Messages
    messages: list[dict]

    # Error
    error: str | None
