"""
Namespace isolation tests for BusinessDocumentProcessorBWorker.

Same shape as the snap and BLA workers: the LanceRAGStore namespace is
fixed at construction, so the store and processor must be job-local.
This worker *writes* ingested chunks, so a leaked store would file a
document under the wrong business.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.background.workers import (
    business_document_processor_worker as worker_module,
)
from app.background.workers.business_document_processor_worker import (
    BusinessDocumentProcessorBWorker,
)


BUSINESS_IDS = [
    "a703974e-f7fe-4779-80d5-d62a21b11fc1",
    "01d7cec4-0b67-4380-ba36-2ff08892c7bf",
    "fa73dbe6-7cee-43f7-9297-ad5bbee2a285",
]


class RecordingRAGStore:
    """Stands in for LanceRAGStore."""

    def __init__(self, namespace: str, scopes: list[str]) -> None:
        self.namespace = namespace
        self.scopes = scopes


class RecordingProcessor:
    """Stands in for DocumentProcessor."""

    calls: list[dict] = []

    def __init__(self, *, store: RecordingRAGStore, event_writer) -> None:
        self.store = store

    async def process(self, *, business_id: str, record_content):
        # Yield mid-call so any shared state can be clobbered by the
        # other jobs before this one reads its store back.
        await asyncio.sleep(0)

        RecordingProcessor.calls.append(
            {
                "business_id": business_id,
                "namespace": self.store.namespace,
                "scopes": self.store.scopes,
            },
        )

        return SimpleNamespace(
            metadata=SimpleNamespace(
                title="t",
                summary="s",
                suggested_questions=[],
            ),
            success=True,
            documents=[],
            chunks=[],
        )


@pytest.fixture
def worker(monkeypatch):
    # Bypass __init__: it opens a DB client and builds an EventWriter.
    instance = BusinessDocumentProcessorBWorker.__new__(
        BusinessDocumentProcessorBWorker,
    )
    instance._job_type = "document_processing"
    instance._worker_name = "document-processing"
    instance._event_writer = object()

    RecordingProcessor.calls = []

    monkeypatch.setattr(worker_module, "LanceRAGStore", RecordingRAGStore)
    monkeypatch.setattr(worker_module, "DocumentProcessor", RecordingProcessor)

    # Neutralise the surrounding I/O: event bus, record writes.
    class NoopBus:
        async def publish(self, event):
            await asyncio.sleep(0)

    monkeypatch.setattr(worker_module, "get_event_bus", lambda: NoopBus())

    async def fake_create_record(business_id, title):
        await asyncio.sleep(0)
        return {"id": f"record-{business_id[:8]}"}

    async def fake_add_record_content(
        business_id, record_id, content_type, content,
    ):
        await asyncio.sleep(0)
        return {"id": f"content-{business_id[:8]}"}

    async def fake_update_record_content(content_id, values):
        await asyncio.sleep(0)
        return {}

    monkeypatch.setattr(worker_module, "create_record", fake_create_record)
    monkeypatch.setattr(
        worker_module, "add_record_content", fake_add_record_content,
    )
    monkeypatch.setattr(
        worker_module, "update_record_content", fake_update_record_content,
    )

    return instance


def _job(business_id: str) -> dict:
    return {
        "id": business_id,
        "job_type": "document_processing",
        "payload": {
            "user_id": "user-1",
            "business_id": business_id,
            "content_type": "text",
            "content": "hello",
        },
    }


async def test_concurrent_jobs_each_use_their_own_namespace(worker):
    await asyncio.gather(
        *(worker.process(_job(business_id)) for business_id in BUSINESS_IDS),
    )

    calls = RecordingProcessor.calls

    assert len(calls) == len(BUSINESS_IDS)

    for call in calls:
        assert call["namespace"] == call["business_id"], (
            f"job for {call['business_id']} wrote to namespace "
            f"{call['namespace']}"
        )

    assert sorted(c["namespace"] for c in calls) == sorted(BUSINESS_IDS)


async def test_concurrent_jobs_each_use_their_own_scopes(worker):
    await asyncio.gather(
        *(worker.process(_job(business_id)) for business_id in BUSINESS_IDS),
    )

    for call in RecordingProcessor.calls:
        business_id = call["business_id"]
        assert call["scopes"][0] == f"business/{business_id}"
        assert call["scopes"][1].startswith(f"business/{business_id}/record/")


async def test_worker_holds_no_shared_processor_state(worker):
    await worker.process(_job(BUSINESS_IDS[0]))

    assert not hasattr(worker, "_processor")
