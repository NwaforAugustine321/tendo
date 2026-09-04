
from __future__ import annotations

from typing import Any, Literal
from enum import StrEnum, Enum

from pydantic import BaseModel, Field


class WebhookType(StrEnum):
    VOICE_TRANSCRIPT = "voice.transcript"
    VOICE_PRESENCE = "voice.presence"
    VOICE_RESPONSE = "voice.response"


class HOOKS(StrEnum):
    VOICE_AGENT = "voice.agent"


class WebhookEvent(BaseModel):
    type: WebhookType
    event_id: str
    request_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
