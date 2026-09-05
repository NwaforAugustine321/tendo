from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PresenceTrackerConfig:
    enabled: bool = True

    intervals: tuple[float, ...] = (
        20.0,
        40.0,
        60.0,
        90.0,
    )

    silence_threshold: float = 5.0
    minimum_response_interval: float = 3.0

    max_response_length: int = 200
    max_concurrent_generations: int = 2

    cancel_on_user_input: bool = True
    cancel_on_completion: bool = True

    metadata: dict[str, object] = field(
        default_factory=dict,
    )
