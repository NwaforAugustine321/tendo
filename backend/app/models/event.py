from typing import Literal

from pydantic import BaseModel, Field


class UnifiedUserEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    thread_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4096)
    channel: Literal["web", "mobile", "whatsapp"]
    input_type: Literal["text", "voice"]
    selected_option_id: str | None = None
    metadata: dict | None = None
