from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


WebhookType = Literal[
    "voice.transcript",
    "voice.presence",
    "voice.response",
]


class WebhookEvent(BaseModel):
    type: WebhookType
    event_id: str
    request_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
