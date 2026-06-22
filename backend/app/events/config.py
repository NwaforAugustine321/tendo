"""ThresholdConfig and scheduler config with optional environment variable overrides."""

import os

from app.events.models import ThresholdConfig


def load_threshold_config() -> ThresholdConfig:
    """
    Load ThresholdConfig with defaults, allowing env var overrides.

    Environment variables:
        EVENT_MIN_EVENT_COUNT: Minimum number of events before job creation
        EVENT_MIN_CHAR_COUNT: Minimum total character count before job creation
        EVENT_MAX_EVENTS_PER_BATCH: Maximum events included in a single job
        EVENT_POLLING_INTERVAL_SECONDS: Seconds between worker poll cycles
        EVENT_MAX_BATCH_SIZE: Maximum events loaded per query
    """
    return ThresholdConfig(
        min_event_count=int(os.environ.get("EVENT_MIN_EVENT_COUNT", "5")),
        min_char_count=int(os.environ.get("EVENT_MIN_CHAR_COUNT", "500")),
        max_events_per_batch=int(os.environ.get("EVENT_MAX_EVENTS_PER_BATCH", "50")),
        polling_interval_seconds=int(os.environ.get("EVENT_POLLING_INTERVAL_SECONDS", "30")),
        max_batch_size=int(os.environ.get("EVENT_MAX_BATCH_SIZE", "100")),
    )


def load_scheduler_config() -> dict:
    """
    Load scheduler configuration from environment.

    Environment variables:
        EVENT_MAX_CONCURRENT_WORKERS: Max businesses processed simultaneously
        EVENT_DISPATCHER_INTERVAL: How often dispatcher checks for ready businesses
        EVENT_IDLE_EVICTION_CYCLES: Remove business after N empty poll cycles
    """
    return {
        "max_concurrent_workers": int(os.environ.get("EVENT_MAX_CONCURRENT_WORKERS", "10")),
        "dispatcher_interval": int(os.environ.get("EVENT_DISPATCHER_INTERVAL", "15")),
        "idle_eviction_cycles": int(os.environ.get("EVENT_IDLE_EVICTION_CYCLES", "3")),
    }
