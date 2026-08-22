"""
Namespace isolation tests for BLABackgroundWorker.

Mirrors the snap worker fix: the learning agent must be job-local so
concurrent jobs in one dispatch batch cannot redirect each other to
another business's LanceDB namespace.
"""

from __future__ import annotations

import asyncio

import pytest

from app.background.workers import bla_worker as bla_worker_module
from app.background.workers.bla_worker import BLABackgroundWorker


BUSINESS_IDS = [
    "a703974e-f7fe-4779-80d5-d62a21b11fc1",
    "01d7cec4-0b67-4380-ba36-2ff08892c7bf",
    "fa73dbe6-7cee-43f7-9297-ad5bbee2a285",
]


class Result:
    def __init__(self, knowledge: str) -> None:
        self.knowledge = knowledge


class RecordingLearningAgent:
    """Stands in for BusinessLearningAgent."""

    calls: list[dict] = []

    def __init__(self, namespace: str, scopes: list[str]) -> None:
        self.namespace = namespace
        self.scopes = scopes

    async def learn(self, *, business_id: str, batch_size: int) -> Result:
        # Yield mid-call so any shared state has the chance to be
        # clobbered by the other jobs before this one finishes.
        await asyncio.sleep(0)

        RecordingLearningAgent.calls.append(
            {
                "business_id": business_id,
                "namespace": self.namespace,
                "scopes": self.scopes,
            },
        )

        return Result(knowledge="")


@pytest.fixture
def worker(monkeypatch):
    # Bypass __init__: it schedules the job-initialization task and
    # builds a LearningEvent, neither of which this test needs.
    instance = BLABackgroundWorker.__new__(BLABackgroundWorker)
    instance._job_type = "bla"
    instance._worker_name = "bla"

    RecordingLearningAgent.calls = []
    monkeypatch.setattr(
        bla_worker_module,
        "BusinessLearningAgent",
        RecordingLearningAgent,
    )

    return instance


def _job(business_id: str) -> dict:
    return {
        "id": business_id,
        "job_type": "bla",
        "payload": {"business_id": business_id, "batch_size": 10},
    }


async def test_concurrent_jobs_each_use_their_own_namespace(worker):
    await asyncio.gather(
        *(worker.process(_job(business_id)) for business_id in BUSINESS_IDS),
    )

    calls = RecordingLearningAgent.calls

    assert len(calls) == len(BUSINESS_IDS)

    for call in calls:
        assert call["namespace"] == call["business_id"], (
            f"job for {call['business_id']} used namespace "
            f"{call['namespace']}"
        )

    assert sorted(c["namespace"] for c in calls) == sorted(BUSINESS_IDS)


async def test_concurrent_jobs_each_use_their_own_scopes(worker):
    await asyncio.gather(
        *(worker.process(_job(business_id)) for business_id in BUSINESS_IDS),
    )

    for call in RecordingLearningAgent.calls:
        assert call["scopes"] == [f"business/{call['business_id']}"]


async def test_worker_holds_no_shared_agent_state(worker):
    await worker.process(_job(BUSINESS_IDS[0]))

    assert not hasattr(worker, "_bla")
    assert not hasattr(type(worker), "bla")


async def test_single_job_still_uses_its_own_namespace(worker):
    business_id = BUSINESS_IDS[0]

    await worker.process(_job(business_id))

    assert RecordingLearningAgent.calls == [
        {
            "business_id": business_id,
            "namespace": business_id,
            "scopes": [f"business/{business_id}"],
        },
    ]
