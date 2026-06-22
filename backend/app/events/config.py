"""Event system configuration loaded from application settings."""

from app.events.models import ThresholdConfig


def load_threshold_config() -> ThresholdConfig:
    """Load ThresholdConfig from application settings."""
    from app.config.settings import settings

    return ThresholdConfig(
        min_event_count=settings.event_min_event_count,
        min_char_count=settings.event_min_char_count,
        max_events_per_batch=settings.event_max_events_per_batch,
        polling_interval_seconds=settings.event_polling_interval_seconds,
        max_batch_size=settings.event_max_batch_size,
    )


def load_scheduler_config() -> dict:
    """Load scheduler configuration from application settings."""
    from app.config.settings import settings

    return {
        "max_concurrent_workers": settings.event_max_concurrent_workers,
        "dispatcher_interval": settings.event_dispatcher_interval,
        "idle_eviction_cycles": settings.event_idle_eviction_cycles,
    }
