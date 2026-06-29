"""Scheduler engine — APScheduler setup, start, stop, and job registration."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the running scheduler instance (or None if not started)."""
    return _scheduler


def start_scheduler() -> None:
    """Start the centralized scheduler with all registered jobs."""
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("Scheduler already running")
        return

    # In-memory job store — fast, no network latency.
    # Jobs re-register on every startup so persistence is not needed.
    _scheduler = AsyncIOScheduler(
        job_defaults={"misfire_grace_time": 30, "coalesce": True},
    )

    # 1. Business event processing (BLA dispatcher)
    from app.scheduler.jobs.business_events import register_event_jobs
    register_event_jobs(_scheduler)

    # 2. Business snapshot generation (every 3 min)
    from app.scheduler.jobs.business_snapshot import register_snapshot_jobs
    register_snapshot_jobs(_scheduler)

    _scheduler.start()
    logger.info("Scheduler started with all jobs registered")


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None
