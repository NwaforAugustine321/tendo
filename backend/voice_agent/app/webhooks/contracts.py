from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from enum import StrEnum, Enum


class HOOKS(StrEnum):
    VOICE_AGENT = "voice.agent"


class WebhookType(StrEnum):
    VOICE_TRANSCRIPT = "voice.transcript"
    VOICE_PRESENCE = "voice.presence"
    VOICE_RESPONSE = "voice.response"


class WebhookEvent(BaseModel):
    type: WebhookType
    event_id: str
    request_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
