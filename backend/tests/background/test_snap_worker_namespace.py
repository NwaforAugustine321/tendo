"""
Regression tests for SnapBackgroundWorker namespace isolation.

A single shared `self._snap` attribute meant every job in a dispatch
batch read the LanceDB namespace of whichever job was constructed last,
so snap runs retrieved memory from the wrong business (usually an empty
namespace, reported as `rows_found=0`).
"""

from __future__ import annotations

import asyncio

import pytest

from app.background.workers import snap_worker as snap_worker_module
from app.background.workers.snap_worker import SnapBackgroundWorker


BUSINESS_IDS = [
    "a703974e-f7fe-4779-80d5-d62a21b11fc1",
    "01d7cec4-0b67-4380-ba36-2ff08892c7bf",
    "fa73dbe6-7cee-43f7-9297-ad5bbee2a285",
]


class RecordingSnapAgent:
    """
    Stands in for SnapAgent.

    Construction is synchronous in the real class too, which is what
    makes the shared-attribute overwrite deterministic rather than
    intermittent.
    """

    def __init__(self, namespace: str, scopes: list[str]) -> None:
        self.namespace = namespace
        self.scopes = scopes

    async def generate(self, *, business_id: str, existing_snaps: list[dict]) -> list:
        # Report the namespace this agent would actually query, so the
        # test can compare it against the job's own business_id.
        RecordingSnapAgent.calls.append(
            {
                "business_id": business_id,
                "namespace": self.namespace,
                "scopes": self.scopes,
            },
        )
        return []


class StubRepository:
    """Yields to the event loop, like the real Redis-backed lookup."""

    async def get_active(self, *, business_id: str, limit: int) -> list:
        await asyncio.sleep(0)
        return []

    async def create(self, *, business_id: str, snap):  # pragma: no cover
        raise AssertionError("No snaps are generated in these tests.")


@pytest.fixture
def worker(monkeypatch):
    # Bypass __init__: it opens Redis, touches Postgres, and schedules
    # the job-initialization task, none of which this test needs.
    instance = SnapBackgroundWorker.__new__(SnapBackgroundWorker)
    instance._job_type = "snap"
    instance._worker_name = "snap"
    instance._repository = StubRepository()

    RecordingSnapAgent.calls = []
    monkeypatch.setattr(snap_worker_module, "SnapAgent", RecordingSnapAgent)

    return instance


def _job(business_id: str) -> dict:
    return {
        "id": business_id,
        "job_type": "snap",
        "payload": {"business_id": business_id},
    }


async def test_concurrent_jobs_each_use_their_own_namespace(worker):
    """
    The regression: all jobs in a batch previously resolved to the
    namespace of the last-constructed agent.
    """

    await asyncio.gather(
        *(worker.process(_job(business_id)) for business_id in BUSINESS_IDS),
    )

    calls = RecordingSnapAgent.calls

    assert len(calls) == len(BUSINESS_IDS)

    for call in calls:
        assert call["namespace"] == call["business_id"], (
            f"job for {call['business_id']} queried namespace "
            f"{call['namespace']}"
        )

    # Every business must be covered exactly once.
    assert sorted(c["namespace"] for c in calls) == sorted(BUSINESS_IDS)


async def test_concurrent_jobs_each_use_their_own_scopes(worker):
    """Scopes are used as the LanceDB filter, so they must match too."""

    await asyncio.gather(
        *(worker.process(_job(business_id)) for business_id in BUSINESS_IDS),
    )

    for call in RecordingSnapAgent.calls:
        assert call["scopes"] == [f"business/{call['business_id']}"]


async def test_worker_holds_no_shared_agent_state(worker):
    """
    The agent must not be reachable from the worker instance, otherwise
    the same overwrite can reappear.
    """

    await worker.process(_job(BUSINESS_IDS[0]))

    assert not hasattr(worker, "_snap")
    assert not hasattr(type(worker), "snap")


async def test_single_job_still_uses_its_own_namespace(worker):
    """Guard the non-concurrent path."""

    business_id = BUSINESS_IDS[0]

    await worker.process(_job(business_id))

    assert RecordingSnapAgent.calls == [
        {
            "business_id": business_id,
            "namespace": business_id,
            "scopes": [f"business/{business_id}"],
        },
    ]
