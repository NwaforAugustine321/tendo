from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass(slots=True)
class PresenceState:
    user_request: str = ""
    status: str = ""
    stage: str = ""
    message: str = ""
    elapsed_seconds: float = 0.0
    max_response_length: int = 200
    iteration: int = 0
    reasoning_step: int = 0
    completed_steps: list[str] = field(
        default_factory=list,
    )
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )
    started_at: float = field(
        default_factory=monotonic,
    )

    @property
    def elapsed(self) -> float:
        return max(
            0.0,
            monotonic() - self.started_at,
        )

    def snapshot(self) -> PresenceState:
        return PresenceState(
            user_request=self.user_request,
            status=self.status,
            stage=self.stage,
            message=self.message,
            elapsed_seconds=self.elapsed,
            max_response_length=self.max_response_length,
            iteration=self.iteration,
            reasoning_step=self.reasoning_step,
            completed_steps=list(
                self.completed_steps,
            ),
            metadata=dict(
                self.metadata,
            ),
            started_at=self.started_at,
        )
