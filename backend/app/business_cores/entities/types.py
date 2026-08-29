from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityInput:
    object_type: str
    data: dict[str, Any]


@dataclass(frozen=True)
class EntityResolution:
    object_type: str
    object_id: str
    created: bool
    status: str | None = None
