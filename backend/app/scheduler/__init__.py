"""Scheduler — centralized APScheduler management.

Start/stop the scheduler and register all background jobs from one place.
"""

from app.scheduler.engine import start_scheduler, stop_scheduler

__all__ = ["start_scheduler", "stop_scheduler"]
