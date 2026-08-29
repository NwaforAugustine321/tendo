from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EventBusConfig:
    """
    Configuration for the application event bus.
    """

    channel: str = "application.events"

    options: dict[str, Any] = field(
        default_factory=dict,
    )
