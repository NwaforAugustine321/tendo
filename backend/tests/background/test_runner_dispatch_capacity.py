"""
Dispatch decoupling tests for BackgroundRunner.

Previously `run_once` awaited every claimed job to completion, so the
dispatch tick lasted as long as the slowest job in the batch and
APScheduler dropped every tick in between ("maximum number of running
instances reached"). Claiming is now capacity-bounded and execution is
detached, so the tick returns immediately.

The RPC is faked here; the real claim path needs Postgres.
"""

from __future__ import annotations

import asyncio

import pytest

from app.background.runner import BackgroundRunner


class FakeRPC:
    def __init__(self, *, pending: int = 0) -> None:
        self.pending = pending
        self.claim_limits: list[int] = []
        self.claim_calls = 0
        self.completed: list[str] = []
        self.failed: list[dict] = []
        self._next_id = 0

    async def claim(self, *, worker_name: str, limit: int) -> list[dict]:
        self.claim_calls += 1
        self.claim_limits.append(limit)

        count = min(limit, self.pending)
        self.pending -= count

        jobs = []
        for _ in range(count):
            self._next_id += 1
            jobs.append(
                {
                    "id": f"job-{self._next_id}",
                    "job_type": "test",
                    "payload": {},
                },
            )
        return jobs

    async def complete(self, *, job_id: str, result: dict) -> None:
        self.completed.append(job_id)

    async def fail(self, *, job_id: str, error: str, retry: bool) -> None:
        self.failed.append({"job_id": job_id, "error": error})

    async def heartbeat(self, *, job_id: str, worker_name: str) -> None:
        return None


class BlockingWorker:
    """Worker that parks until released, standing in for a slow job."""

    def __init__(self) -> None:
        self.gate = asyncio.Event()
        self.started = 0

    async def run(self, job: dict) -> dict:
        self.started += 1
        await self.gate.wait()
        return {}


class FailingWorker:
    async def run(self, job: dict) -> dict:
        raise RuntimeError("boom")


class FakeRegistry:
    def __init__(self, worker) -> None:
        self._worker = worker

    def get(self, job_type: str):
        return self._worker


def _runner(rpc, worker, *, max_concurrency: int = 10) -> BackgroundRunner:
    return BackgroundRunner(
        rpc=rpc,
        registry=FakeRegistry(worker),
        worker_name="test-worker",
        heartbeat_interval=30.0,
        max_concurrency=max_concurrency,
    )


async def test_run_once_returns_without_awaiting_job_completion():
    """The regression: the tick must not block on job duration."""

    rpc = FakeRPC(pending=3)
    worker = BlockingWorker()
    runner = _runner(rpc, worker)

    claimed = await asyncio.wait_for(runner.run_once(limit=10), timeout=1.0)

    assert claimed == 3
    assert runner.in_flight == 3

    # Jobs are genuinely still running, not silently skipped.
    await asyncio.sleep(0)
    assert worker.started == 3
    assert rpc.completed == []

    worker.gate.set()
    assert await runner.drain(timeout=1.0) == 0
    assert sorted(rpc.completed) == ["job-1", "job-2", "job-3"]


async def test_claim_limit_is_capped_by_free_capacity():
    rpc = FakeRPC(pending=100)
    worker = BlockingWorker()
    runner = _runner(rpc, worker, max_concurrency=4)

    assert await runner.run_once(limit=10) == 4
    assert rpc.claim_limits == [4]

    worker.gate.set()
    await runner.drain(timeout=1.0)


async def test_at_capacity_tick_claims_nothing_and_does_not_hit_rpc():
    rpc = FakeRPC(pending=100)
    worker = BlockingWorker()
    runner = _runner(rpc, worker, max_concurrency=2)

    assert await runner.run_once(limit=10) == 2
    assert runner.available_capacity == 0

    calls_before = rpc.claim_calls

    # A tick while saturated must return immediately without claiming,
    # so no job is marked running while it waits to start.
    assert await asyncio.wait_for(runner.run_once(limit=10), timeout=1.0) == 0
    assert rpc.claim_calls == calls_before

    worker.gate.set()
    await runner.drain(timeout=1.0)


async def test_capacity_is_released_as_jobs_finish():
    rpc = FakeRPC(pending=6)
    worker = BlockingWorker()
    runner = _runner(rpc, worker, max_concurrency=3)

    assert await runner.run_once(limit=10) == 3
    assert runner.available_capacity == 0

    worker.gate.set()
    await runner.drain(timeout=1.0)

    assert runner.in_flight == 0
    assert runner.available_capacity == 3

    # The next tick can now claim the remaining jobs.
    assert await runner.run_once(limit=10) == 3


async def test_failed_job_still_releases_capacity():
    rpc = FakeRPC(pending=2)
    runner = _runner(rpc, FailingWorker(), max_concurrency=2)

    assert await runner.run_once(limit=10) == 2

    await runner.drain(timeout=1.0)

    assert runner.in_flight == 0
    assert runner.available_capacity == 2
    assert len(rpc.failed) == 2
    assert rpc.completed == []


async def test_drain_with_no_jobs_is_a_noop():
    runner = _runner(FakeRPC(), BlockingWorker())

    assert await runner.drain(timeout=1.0) == 0


async def test_drain_reports_jobs_still_running_on_timeout():
    rpc = FakeRPC(pending=1)
    worker = BlockingWorker()
    runner = _runner(rpc, worker)

    await runner.run_once(limit=10)

    # Never released: drain must give up rather than hang shutdown.
    assert await runner.drain(timeout=0.05) == 1

    worker.gate.set()
    await runner.drain(timeout=1.0)


async def test_no_pending_jobs_claims_nothing():
    rpc = FakeRPC(pending=0)
    runner = _runner(rpc, BlockingWorker())

    assert await runner.run_once(limit=10) == 0
    assert runner.in_flight == 0


async def test_max_concurrency_must_be_positive():
    with pytest.raises(ValueError):
        _runner(FakeRPC(), BlockingWorker(), max_concurrency=0)
