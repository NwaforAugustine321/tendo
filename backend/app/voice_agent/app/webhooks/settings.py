from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .contracts import WebhookType


class WebhookSendHook(BaseModel):
    url: str
    events: set[WebhookType] = Field(default_factory=set)

    @field_validator("events", mode="before")
    @classmethod
    def parse_events(cls, v: Any) -> Any:
        if isinstance(v, str):
            return set(json.loads(v))
        return v


class WebhookReceiveHook(BaseModel):
    events: set[WebhookType] = Field(default_factory=set)

    @field_validator("events", mode="before")
    @classmethod
    def parse_events(cls, v: Any) -> Any:
        if isinstance(v, str):
            return set(json.loads(v))
        return v


class WebhookSettings(BaseModel):
    send_hooks: dict[str, WebhookSendHook] = Field(default_factory=dict)
    receive_hooks: dict[str, WebhookReceiveHook] = Field(default_factory=dict)
    secret: str
    timeout: float = 30.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    webhook: WebhookSettings


settings = Settings()
