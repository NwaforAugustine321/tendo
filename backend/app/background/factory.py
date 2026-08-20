from __future__ import annotations

import logging
from collections.abc import Iterable

from .config import BackgroundJobConfig
from .dispatcher import BackgroundDispatcher
from .interfaces import BackgroundJobRPC
from .registry import WorkerRegistry
from .rpc import DatabaseBackgroundJobRPC
from .runner import BackgroundRunner
from .scheduler import BackgroundScheduler
from .worker import BackgroundWorker
from .workers.bla_worker import BLABackgroundWorker
from .workers.business_document_processor_worker import BusinessDocumentProcessorBWorker
from .interfaces import IntervalUnit

logger = logging.getLogger(__name__)


class BackgroundJobSystem:
    """
    Fully assembled durable background-job system.

    Architecture:

        BackgroundJobRPC
              ↓
        WorkerRegistry
              ↓
        BackgroundRunner
              ↓
        BackgroundDispatcher
              ↓
        BackgroundScheduler

    Responsibilities:

        RPC:
            Durable database operations.

        Registry:
            Worker discovery.

        Runner:
            Job execution and heartbeats.

        Dispatcher:
            Dispatch and stale-job recovery.

        Scheduler:
            Timing only.

    This class acts as the application-facing facade for the
    complete background-job infrastructure.
    """

    def __init__(
        self,
        *,
        config: BackgroundJobConfig,
        rpc: BackgroundJobRPC,
        registry: WorkerRegistry,
        runner: BackgroundRunner,
        dispatcher: BackgroundDispatcher,
        scheduler: BackgroundScheduler,
    ) -> None:
        self._config = config
        self._rpc = rpc
        self._registry = registry
        self._runner = runner
        self._dispatcher = dispatcher
        self._scheduler = scheduler

    # ==================================================================
    # Properties
    # ==================================================================

    @property
    def config(self) -> BackgroundJobConfig:
        """Return the background-job configuration."""

        return self._config

    @property
    def rpc(self) -> BackgroundJobRPC:
        """Return the durable background-job RPC implementation."""

        return self._rpc

    @property
    def registry(self) -> WorkerRegistry:
        """Return the worker registry."""

        return self._registry

    @property
    def runner(self) -> BackgroundRunner:
        """Return the background-job runner."""

        return self._runner

    @property
    def dispatcher(self) -> BackgroundDispatcher:
        """Return the background-job dispatcher."""

        return self._dispatcher

    @property
    def scheduler(self) -> BackgroundScheduler:
        """Return the APScheduler integration."""

        return self._scheduler

    @property
    def worker_name(self) -> str:
        """Return the configured worker name."""

        return self._config.worker_name

    @property
    def started(self) -> bool:
        """Return whether the background-job scheduler is running."""

        return self._scheduler.started

    # ==================================================================
    # Lifecycle
    # ==================================================================

    def start(self) -> None:
        """
        Start the background-job system.

        Starting the system starts APScheduler.

        APScheduler then independently triggers:

            - job dispatch
            - stale-job recovery
        """

        if self.started:
            logger.warning(
                "[BackgroundJobSystem] "
                "Background job system already started: "
                "worker=%s",
                self.worker_name,
            )
            return

        self._scheduler.start()

        logger.info(
            "[BackgroundJobSystem] "
            "Background job system started: "
            "worker=%s",
            self.worker_name,
        )

    async def shutdown(
        self,
        *,
        wait: bool = True,
    ) -> None:
        """
        Shut down the background-job system.

        Args:
            wait:
                Whether APScheduler should wait for currently
                executing scheduled jobs.
        """

        if not self.started:
            return

        logger.info(
            "[BackgroundJobSystem] "
            "Shutting down: worker=%s",
            self.worker_name,
        )

        await self._scheduler.shutdown(
            wait=wait,
        )

        logger.info(
            "[BackgroundJobSystem] "
            "Background job system stopped: worker=%s",
            self.worker_name,
        )


# ======================================================================
# Factory
# ======================================================================


def create_background_job_system(
    *,
    config: BackgroundJobConfig | None = None,
    rpc: BackgroundJobRPC | None = None,
    workers: Iterable[BackgroundWorker] | None = None,
) -> BackgroundJobSystem:
    """
    Construct the complete durable background-job system.

    Dependency construction order:

        1. Configuration
        2. RPC
        3. Worker registry
        4. Runner
        5. Dispatcher
        6. Scheduler
        7. BackgroundJobSystem

    Args:
        config:
            Background-job configuration.

            If omitted, configuration is loaded from environment
            variables.

        rpc:
            Optional BackgroundJobRPC implementation.

            If omitted, DatabaseBackgroundJobRPC is used.

        workers:
            Application-specific BackgroundWorker instances.

            Each worker handles exactly one job type.

    Returns:
        Fully assembled BackgroundJobSystem.

    Raises:
        ValueError:
            If the configuration or worker registration is invalid.

        TypeError:
            If an invalid worker is supplied to the registry.
    """

    # ==================================================================
    # 1. Configuration
    # ==================================================================

    if config is None:
        config = BackgroundJobConfig.from_env()

    config.validate()

    logger.debug(
        "[BackgroundJobFactory] "
        "Configuration loaded: "
        "worker=%s "
        "batch_size=%s "
        "dispatch_interval=%ss "
        "recovery_interval=%ss",
        config.worker_name,
        config.batch_size,
        config.dispatch_interval_seconds,
        config.recovery_interval_seconds,
    )

    # ==================================================================
    # 2. Durable RPC
    # ==================================================================

    if rpc is None:
        rpc = DatabaseBackgroundJobRPC()

    # ==================================================================
    # 3. Worker Registry
    # ==================================================================

    application_workers = list(
        workers or [],
    )

    application_workers.append(
        BLABackgroundWorker(rpc=rpc),
    )

    application_workers.append(
        BusinessDocumentProcessorBWorker()
    )

    registry = WorkerRegistry(
        workers=application_workers,
    )

    # ==================================================================
    # 4. Runner
    # ==================================================================

    runner = BackgroundRunner(
        rpc=rpc,
        registry=registry,
        worker_name=config.worker_name,
        heartbeat_interval=(
            config.heartbeat_interval_seconds
        ),
    )

    # ==================================================================
    # 5. Dispatcher
    # ==================================================================

    dispatcher = BackgroundDispatcher(
        rpc=rpc,
        runner=runner,
        batch_size=config.batch_size,
        recovery_timeout=(
            config.recovery_timeout_seconds
        ),
    )

    # ==================================================================
    # 6. Scheduler
    # ==================================================================

    scheduler = BackgroundScheduler(
        dispatcher=dispatcher,
        config=config,
    )

    # ==================================================================
    # 7. System Facade
    # ==================================================================

    system = BackgroundJobSystem(
        config=config,
        rpc=rpc,
        registry=registry,
        runner=runner,
        dispatcher=dispatcher,
        scheduler=scheduler,
    )

    logger.info(
        "[BackgroundJobFactory] "
        "Background job system created: "
        "worker=%s "
        "workers=%s "
        "batch_size=%s "
        "dispatch_interval=%ss "
        "recovery_interval=%ss "
        "heartbeat_interval=%ss "
        "recovery_timeout=%ss",
        config.worker_name,
        len(registry),
        config.batch_size,
        config.dispatch_interval_seconds,
        config.recovery_interval_seconds,
        config.heartbeat_interval_seconds,
        config.recovery_timeout_seconds,
    )

    return system


async def create_task(
    job_type: str,
    payload: dict[str, Any],
    run_at: str | None = None,
    interval_value: int | None = None,
    interval_unit: IntervalUnit | None = None,
    id: str = '',
    priority: int = 0,
    max_attempts: int = 2
):
    try:
        rpc = DatabaseBackgroundJobRPC()
        await rpc.enqueue(
            job_type=job_type,
            id=id,
            run_at=run_at,
            payload=payload,
            interval_value=interval_value,
            interval_unit=interval_unit,
            priority=priority,
            max_attempts=max_attempts
        )
    except Exception as exec:
        raise exec
