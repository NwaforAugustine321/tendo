from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PresenceTrackerConfig:
    enabled: bool = True

    intervals: tuple[float, ...] = (
        40.0,
        60.0,
        90.0,
        120.0,
    )

    silence_threshold: float = 8.0
    minimum_response_interval: float = 5.0

    max_response_length: int = 160
    max_concurrent_generations: int = 1

    cancel_on_user_input: bool = True
    cancel_on_completion: bool = True

    metadata: dict[str, object] = field(
        default_factory=dict,
    )
