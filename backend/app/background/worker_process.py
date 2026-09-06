from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from multiprocessing import get_context
from typing import Any

from .config import BackgroundJobConfig
from .factory import create_background_worker_runner

logger = logging.getLogger(__name__)


def _run_worker_process(
    worker_id: int,
    stop_event: Any,
) -> None:
    """
    Spawn-safe entry point for an individual worker process.

    The child loads its own configuration from the environment so the parent
    does not need to pickle the application configuration when using the
    spawn multiprocessing context.
    """
    config = BackgroundJobConfig.from_env()

    worker = BackgroundWorkerProcess(
        worker_id=worker_id,
        config=config,
        stop_event=stop_event,
    )

    try:
        worker.run()

    except KeyboardInterrupt:
        return

    except Exception:
        logger.exception(
            "[BackgroundWorkerProcess] "
            "Worker process crashed: "
            "worker_id=%s pid=%s",
            worker_id,
            os.getpid(),
        )
        raise


class BackgroundWorkerProcess:
    def __init__(
        self,
        *,
        worker_id: int,
        config: BackgroundJobConfig,
        stop_event: Any,
    ) -> None:
        self._worker_id = worker_id
        self._config = config
        self._stop_event = stop_event

    def run(self) -> None:
        asyncio.run(
            self._run(),
        )

    async def _run(self) -> None:
        logger.info(
            "[BackgroundWorkerProcess] Starting worker process: "
            "worker_id=%s pid=%s",
            self._worker_id,
            os.getpid(),
        )

        runner = create_background_worker_runner(
            config=self._config,
        )

        logger.info(
            "[BackgroundWorkerProcess] Worker ready: "
            "worker_id=%s pid=%s worker_name=%s "
            "max_concurrency=%s",
            self._worker_id,
            os.getpid(),
            runner.worker_name,
            runner.max_concurrency,
        )

        try:
            while not self._stop_event.is_set():
                try:
                    await runner.run_once(
                        limit=self._config.batch_size,
                    )

                except asyncio.CancelledError:
                    raise

                except Exception:
                    logger.exception(
                        "[BackgroundWorkerProcess] "
                        "Worker cycle failed: "
                        "worker_id=%s pid=%s",
                        self._worker_id,
                        os.getpid(),
                    )

                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(
                            self._stop_event.wait,
                            self._config.dispatch_interval_seconds,
                        ),
                        timeout=(
                            self._config.dispatch_interval_seconds
                        ),
                    )

                except asyncio.TimeoutError:
                    continue

        finally:
            logger.info(
                "[BackgroundWorkerProcess] "
                "Draining worker: worker_id=%s pid=%s",
                self._worker_id,
                os.getpid(),
            )

            try:
                await runner.drain(
                    timeout=self._config.recovery_timeout_seconds,
                )
            except Exception:
                logger.exception(
                    "[BackgroundWorkerProcess] "
                    "Worker drain failed: "
                    "worker_id=%s pid=%s",
                    self._worker_id,
                    os.getpid(),
                )

            logger.info(
                "[BackgroundWorkerProcess] "
                "Worker stopped: worker_id=%s pid=%s",
                self._worker_id,
                os.getpid(),
            )


class BackgroundWorkerManager:
    def __init__(
        self,
        *,
        config: BackgroundJobConfig | None = None,
        worker_count: int | None = None,
        restart_delay: float = 2.0,
    ) -> None:
        if config is None:
            config = BackgroundJobConfig.from_env()

        config.validate()

        if worker_count is None:
            worker_count = self._get_worker_count()

        if worker_count <= 0:
            raise ValueError(
                "worker_count must be greater than zero."
            )

        if restart_delay < 0:
            raise ValueError(
                "restart_delay cannot be negative."
            )

        self._config = config
        self._worker_count = worker_count
        self._restart_delay = restart_delay

        # Use one explicit multiprocessing context for all supported
        # operating systems. Spawn is safe on Windows and macOS and also
        # works on Linux without relying on fork-specific behavior.
        self._mp_context = get_context("spawn")

        self._stop_event: Any = None
        self._processes: dict[int, Process] = {}
        self._stopping = False

    @staticmethod
    def _get_worker_count() -> int:
        value = os.getenv(
            "BACKGROUND_WORKERS",
        )

        if value:
            try:
                worker_count = int(value)
            except ValueError as exc:
                raise ValueError(
                    "BACKGROUND_WORKERS must be an integer."
                ) from exc

            if worker_count > 0:
                return worker_count

        cpu_count = os.cpu_count() or 1

        return max(
            1,
            cpu_count,
        )

    @property
    def worker_count(self) -> int:
        return self._worker_count

    @property
    def processes(self) -> dict[int, Process]:
        return dict(self._processes)

    def start(self) -> None:
        if self._processes:
            logger.warning(
                "[BackgroundWorkerManager] "
                "Manager already started."
            )
            return

        self._stopping = False
        self._stop_event = self._mp_context.Event()

        logger.info(
            "[BackgroundWorkerManager] "
            "Starting worker manager: workers=%s "
            "worker_name=%s batch_size=%s",
            self._worker_count,
            self._config.worker_name,
            self._config.batch_size,
        )

        for worker_id in range(
            1,
            self._worker_count + 1,
        ):
            self._start_worker(
                worker_id,
            )

    def run(self) -> None:
        self.start()

        try:
            while not self._stopping:
                self._monitor_workers()

                if self._stopping:
                    break

                time.sleep(
                    min(
                        1.0,
                        max(
                            0.1,
                            self._restart_delay,
                        ),
                    ),
                )

        except KeyboardInterrupt:
            logger.info(
                "[BackgroundWorkerManager] "
                "Keyboard interrupt received."
            )

        finally:
            self.stop()

    def _start_worker(
        self,
        worker_id: int,
    ) -> None:
        if self._stop_event is None:
            raise RuntimeError(
                "Worker manager has not been started."
            )

        process = self._mp_context.Process(
            target=_run_worker_process,
            args=(
                worker_id,
                self._stop_event,
            ),
            name=(
                f"background-worker-{worker_id}"
            ),
        )

        process.start()

        self._processes[
            worker_id
        ] = process

        logger.info(
            "[BackgroundWorkerManager] "
            "Worker process started: "
            "worker_id=%s pid=%s",
            worker_id,
            process.pid,
        )

    def _monitor_workers(self) -> None:
        if self._stopping:
            return

        for worker_id, process in list(
            self._processes.items(),
        ):
            if process.is_alive():
                continue

            exit_code = process.exitcode

            logger.error(
                "[BackgroundWorkerManager] "
                "Worker stopped unexpectedly: "
                "worker_id=%s pid=%s exit_code=%s",
                worker_id,
                process.pid,
                exit_code,
            )

            process.join(
                timeout=0,
            )

            self._processes.pop(
                worker_id,
                None,
            )

            if self._stopping:
                continue

            if self._restart_delay > 0:
                time.sleep(
                    self._restart_delay,
                )

            if not self._stopping:
                logger.info(
                    "[BackgroundWorkerManager] "
                    "Restarting worker: worker_id=%s",
                    worker_id,
                )

                self._start_worker(
                    worker_id,
                )

    def stop(
        self,
        *,
        timeout: float = 30.0,
    ) -> None:
        if self._stopping:
            return

        self._stopping = True

        logger.info(
            "[BackgroundWorkerManager] "
            "Stopping worker manager."
        )

        if self._stop_event is not None:
            self._stop_event.set()

        deadline = time.monotonic() + max(
            0.0,
            timeout,
        )

        for worker_id, process in list(
            self._processes.items(),
        ):
            remaining = max(
                0.0,
                deadline - time.monotonic(),
            )

            process.join(
                timeout=remaining,
            )

            if process.is_alive():
                logger.warning(
                    "[BackgroundWorkerManager] "
                    "Worker did not stop gracefully; "
                    "terminating: worker_id=%s pid=%s",
                    worker_id,
                    process.pid,
                )

                process.terminate()

                remaining = max(
                    0.0,
                    deadline - time.monotonic(),
                )

                process.join(
                    timeout=remaining,
                )

            if process.is_alive():
                logger.error(
                    "[BackgroundWorkerManager] "
                    "Worker could not be terminated: "
                    "worker_id=%s pid=%s",
                    worker_id,
                    process.pid,
                )

            else:
                logger.info(
                    "[BackgroundWorkerManager] "
                    "Worker stopped: "
                    "worker_id=%s pid=%s",
                    worker_id,
                    process.pid,
                )

        self._processes.clear()

        logger.info(
            "[BackgroundWorkerManager] "
            "Worker manager stopped."
        )


def main() -> None:
    get_context("spawn").freeze_support()

    logging.basicConfig(
        level=os.getenv(
            "LOG_LEVEL",
            "INFO",
        ),
    )

    config = BackgroundJobConfig.from_env()

    logger.info(
        "[BackgroundWorkerManager] "
        "Background worker process starting: "
        "pid=%s log_level=%s",
        os.getpid(),
        os.getenv("LOG_LEVEL", "INFO"),
    )

    manager = BackgroundWorkerManager(
        config=config,
    )

    def shutdown(
        signum: int,
        frame: Any,
    ) -> None:
        logger.info(
            "[BackgroundWorkerManager] "
            "Shutdown signal received: signal=%s",
            signum,
        )

        manager.stop()

    signal.signal(
        signal.SIGINT,
        shutdown,
    )

    signal.signal(
        signal.SIGTERM,
        shutdown,
    )

    manager.run()


if __name__ == "__main__":
    main()
