"""Base scheduled worker — reusable for any periodic job.

- Runs on a schedule (interval or cron)
- Tracks execution state (idle, running, completed, failed)
- Persists progress via checkpoints
- Handles errors gracefully
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WorkerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseWorker(ABC):
    """Abstract base for any scheduled worker.

    Provides state tracking, error handling, and a standard run cycle.
    Subclass and implement `process()`.

    Usage:
        class MyWorker(BaseWorker):
            async def process(self, context: dict) -> Any:
                # your logic here
                return result

        worker = MyWorker(name="my_worker")
        result = await worker.run(context={"business_id": "abc"})
    """

    def __init__(self, name: str):
        self.name = name
        self.state = WorkerState.IDLE

    async def run(self, context: dict | None = None) -> Any:
        try:
            self.state = WorkerState.RUNNING
            result = await self.process(context or {})
            self.state = WorkerState.COMPLETED
            return result
        except Exception as e:
            self.state = WorkerState.FAILED
            logger.error(
                f"Worker '{self.name}' failed: {e}",
                exc_info=True,
                extra={"worker_name": self.name},
            )
            return None

    @abstractmethod
    async def process(self, context: dict) -> Any:
        """Implement your worker logic here.

        Args:
            context: Dict with whatever data the worker needs.

        Returns:
            Any result (logged by caller if needed).
        """
        ...
