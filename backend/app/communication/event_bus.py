from __future__ import annotations

from app.communication.interfaces import EventBus


_event_bus: EventBus | None = None


def set_event_bus(
    event_bus: EventBus,
) -> None:
    """Set the process-local application EventBus."""

    global _event_bus

    _event_bus = event_bus


def get_event_bus() -> EventBus:
    """Return the process-local application EventBus."""

    if _event_bus is None:
        raise RuntimeError(
            "Application EventBus has not been initialized.",
        )

    return _event_bus


def clear_event_bus() -> None:
    """Clear the process-local EventBus."""

    global _event_bus

    _event_bus = None
