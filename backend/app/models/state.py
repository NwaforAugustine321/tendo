"""Graph state definition."""

import operator
from collections.abc import Callable
from typing import Annotated, Any, Literal, TypedDict


class GraphState(TypedDict, total=False):
    event: dict
    user_id: str | None
    thread_id: str | None
    business_id: str | None
    output_mode: Literal["conversation"] | None
    response: dict | None
    messages: Annotated[list[dict], operator.add]
    error: str | None
    pending_question: str | None
    thinking_callback: Any
