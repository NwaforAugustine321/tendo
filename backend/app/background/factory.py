
from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from .config import BackgroundJobConfig
from .dispatcher import BackgroundDispatcher
from .interfaces import BackgroundJobRPC, IntervalUnit
from .registry import WorkerRegistry
from .rpc import DatabaseBackgroundJobRPC
from .runner import BackgroundRunner
from .scheduler import BackgroundScheduler
from .worker import BackgroundWorker
from .workers.bla_worker import BLABackgroundWorker
from .workers.document_processor_worker import DocumentProcessorWorker
from .workers.snap_worker import SnapBackgroundWorker

logger = logging.getLogger(__name__)


class BackgroundJobSystem:
    """
    Fully assembled background-job scheduler/recovery system.

    Architecture:

        BackgroundJobRPC
              ↓
        BackgroundDispatcher
              ↓
        BackgroundScheduler

    Worker execution is intentionally not part of this system.

    Background workers run independently through
    create_background_worker_runner().

    Responsibilities:

        RPC:
            Durable database operations.

        Dispatcher:
            Stale-job recovery.

        Scheduler:
            Recovery timing.

    This class acts as the application-facing facade for the
    scheduler/recovery infrastructure.
    """

    def __init__(
        self,
        *,
        config: BackgroundJobConfig,
        rpc: BackgroundJobRPC,
        dispatcher: BackgroundDispatcher,
        scheduler: BackgroundScheduler,
    ) -> None:
        self._config = config
        self._rpc = rpc
        self._dispatcher = dispatcher
        self._scheduler = scheduler

    @property
    def config(self) -> BackgroundJobConfig:
        return self._config

    @property
    def rpc(self) -> BackgroundJobRPC:
        return self._rpc

    @property
    def dispatcher(self) -> BackgroundDispatcher:
        return self._dispatcher

    @property
    def scheduler(self) -> BackgroundScheduler:
        return self._scheduler

    @property
    def worker_name(self) -> str:
        return self._config.worker_name

    @property
    def started(self) -> bool:
        return self._scheduler.started

    def start(self) -> None:
        if self.started:
            logger.warning(
                "[BackgroundJobSystem] "
                "Background job system already started.",
            )
            return

        self._scheduler.start()

        logger.info(
            "[BackgroundJobSystem] "
            "Background scheduler/recovery system started.",
        )

    async def shutdown(
        self,
        *,
        wait: bool = True,
    ) -> None:
        if not self.started:
            return

        logger.info(
            "[BackgroundJobSystem] "
            "Shutting down background scheduler/recovery system.",
        )

        await self._scheduler.shutdown(
            wait=wait,
        )

        logger.info(
            "[BackgroundJobSystem] "
            "Background scheduler/recovery system stopped.",
        )


def _load_config(
    config: BackgroundJobConfig | None,
) -> BackgroundJobConfig:
    if config is None:
        config = BackgroundJobConfig.from_env()

    config.validate()

    return config


def _create_rpc(
    rpc: BackgroundJobRPC | None,
) -> BackgroundJobRPC:
    if rpc is None:
        rpc = DatabaseBackgroundJobRPC()

    return rpc


def _create_workers(
    *,
    rpc: BackgroundJobRPC,
    workers: Iterable[BackgroundWorker] | None = None,
) -> list[BackgroundWorker]:
    application_workers = list(
        workers or [],
    )

    application_workers.append(
        BLABackgroundWorker(
            rpc=rpc,
        ),
    )

    application_workers.append(
        SnapBackgroundWorker(
            rpc=rpc,
        ),
    )

    application_workers.append(
        DocumentProcessorWorker(),
    )

    return application_workers


def _create_registry(
    *,
    rpc: BackgroundJobRPC,
    workers: Iterable[BackgroundWorker] | None = None,
) -> WorkerRegistry:
    application_workers = _create_workers(
        rpc=rpc,
        workers=workers,
    )

    return WorkerRegistry(
        workers=application_workers,
    )


def create_background_worker_runner(
    *,
    config: BackgroundJobConfig | None = None,
    rpc: BackgroundJobRPC | None = None,
    workers: Iterable[BackgroundWorker] | None = None,
) -> BackgroundRunner:
    """
    Create a standalone background worker runner.

    This factory intentionally does not create or start
    BackgroundDispatcher or BackgroundScheduler.

    It is used by external OS-level worker processes.
    """

    config = _load_config(
        config,
    )

    rpc = _create_rpc(
        rpc,
    )

    registry = _create_registry(
        rpc=rpc,
        workers=workers,
    )

    runner = BackgroundRunner(
        rpc=rpc,
        registry=registry,
        worker_name=config.worker_name,
        heartbeat_interval=(
            config.heartbeat_interval_seconds
        ),
        max_concurrency=(
            config.effective_max_concurrency
        ),
    )

    logger.info(
        "[BackgroundJobFactory] "
        "Background worker runner created: "
        "worker=%s "
        "workers=%s "
        "max_concurrency=%s",
        config.worker_name,
        len(registry),
        config.effective_max_concurrency,
    )

    return runner


def create_background_job_system(
    *,
    config: BackgroundJobConfig | None = None,
    rpc: BackgroundJobRPC | None = None,
) -> BackgroundJobSystem:
    """
    Construct the scheduler/recovery portion of the durable
    background-job system.

    Dependency construction order:

        1. Configuration
        2. RPC
        3. Dispatcher
        4. Scheduler
        5. BackgroundJobSystem

    This factory does not create a worker registry or runner.

    Worker execution is handled independently by
    create_background_worker_runner().
    """

    config = _load_config(
        config,
    )

    logger.debug(
        "[BackgroundJobFactory] "
        "Configuration loaded: "
        "worker=%s "
        "recovery_interval=%ss",
        config.worker_name,
        config.recovery_interval_seconds,
    )

    rpc = _create_rpc(
        rpc,
    )

    dispatcher = BackgroundDispatcher(
        rpc=rpc,
        recovery_timeout=(
            config.recovery_timeout_seconds
        ),
    )

    scheduler = BackgroundScheduler(
        dispatcher=dispatcher,
        config=config,
    )

    system = BackgroundJobSystem(
        config=config,
        rpc=rpc,
        dispatcher=dispatcher,
        scheduler=scheduler,
    )

    logger.info(
        "[BackgroundJobFactory] "
        "Background scheduler/recovery system created: "
        "worker=%s "
        "recovery_interval=%ss "
        "recovery_timeout=%ss",
        config.worker_name,
        config.recovery_interval_seconds,
        config.recovery_timeout_seconds,
    )

    return system


async def create_task(
    job_type: str,
    payload: dict[str, Any],
    run_at: str | None = None,
    interval_value: int | None = None,
    interval_unit: IntervalUnit | None = None,
    id: str = "",
    priority: int = 0,
    max_attempts: int = 2,
) -> None:
    rpc = DatabaseBackgroundJobRPC()

    await rpc.enqueue(
        job_type=job_type,
        id=id,
        run_at=run_at,
        payload=payload,
        interval_value=interval_value,
        interval_unit=interval_unit,
        priority=priority,
        max_attempts=max_attempts,
    )
