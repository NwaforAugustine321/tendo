from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GuardrailConfig(BaseModel):
    config_dir: str = Field(default="guardrails/config")
    passthrough: bool = Field(default=True)


class GuardrailResult(BaseModel):
    allowed: bool = True
    response: Any = None
