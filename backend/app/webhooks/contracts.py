
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WebhookType(StrEnum):
    VOICE_TRANSCRIPT = "voice.transcript"
    VOICE_PRESENCE = "voice.presence"
    VOICE_RESPONSE = "voice.response"
    DOCUMENT_INGESTION = "document.ingestion"


class HOOKS(StrEnum):
    VOICE_AGENT = "voice.agent"


class WebhookEvent(BaseModel):
    type: WebhookType
    event_id: str
    request_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
