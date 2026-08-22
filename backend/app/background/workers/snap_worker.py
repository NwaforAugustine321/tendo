from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..interfaces import (
    BackgroundJobRPC,
    IntervalUnit,
)
from ..worker import BackgroundWorker

from ...runtime.agent_hub.snap.agent import (
    SnapAgent,
)
from ...runtime.agent_hub.snap.persist_store import (
    SnapPersistence,
)
from ...runtime.agent_hub.snap.repository import (
    SnapRepository,
)
from ...runtime.agent_hub.snap.service import (
    SnapService,
)
from ...communication.transports.redis import (
    create_redis_transport
)
from app.config import settings

logger = logging.getLogger(__name__)


class SnapBackgroundWorker(
    BackgroundWorker,
):
    """
    Background worker for Snap generation jobs.

    """

    def __init__(
        self,
        *,
        rpc: BackgroundJobRPC,
    ) -> None:

        super().__init__(
            job_type="snap",
            worker_name="snap",
        )

        if rpc is None:
            raise ValueError(
                "'rpc' instance not found.",
            )

        self._rpc = rpc

        persistence = SnapPersistence()

        service = SnapService(
            redis=create_redis_transport(
                url=settings.redis_url,
            )
        )

        self._repository = SnapRepository(
            service=service,
            persistence=persistence,
        )

        task = asyncio.create_task(
            self._initialize_business_snap_jobs(
                page_size=100,
            ),
        )

        task.add_done_callback(
            self._on_init_done,
        )

    @staticmethod
    def _on_init_done(
        task: asyncio.Task,
    ) -> None:

        if task.cancelled():
            return

        exc = task.exception()

        if exc:

            logger.error(
                "Snap job initialization failed: %s",
                exc,
                exc_info=exc,
            )

    async def _initialize_business_snap_jobs(
        self,
        *,
        page_size: int,
    ) -> int:

        if page_size <= 0:
            raise ValueError(
                "page_size must be greater than zero.",
            )

        offset = 0
        total = 0

        while True:

            business_ids = (
                await self._repository.fetch_business_ids(
                    offset=offset,
                    limit=page_size,
                )
            )

            if not business_ids:
                break

            for business_id in business_ids:

                if not isinstance(
                    business_id,
                    str,
                ):
                    continue

                business_id = business_id.strip()

                if not business_id:
                    continue

                await self._rpc.enqueue(
                    job_type=self.job_type,
                    id=business_id,
                    payload={
                        "business_id": business_id,
                    },
                    interval_value=12,
                    interval_unit=IntervalUnit.HOURS,
                )

                total += 1

            if len(
                business_ids,
            ) < page_size:
                break

            offset += page_size

        logger.info(
            "Snap job initialization complete: "
            "businesses=%s",
            total,
        )

        return total

    async def process(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any] | None:

        job_id = self.get_id(
            job,
        )

        if job_id is None:
            raise ValueError(
                "Snap job requires 'id'.",
            )

        if not isinstance(
            job_id,
            str,
        ):
            raise TypeError(
                "Snap job 'id' must be a string.",
            )

        business_id = job_id.strip()

        if not business_id:
            raise ValueError(
                "Snap job 'id' cannot be empty.",
            )

        payload = self.get_payload(
            job,
        )

        payload_business_id = payload.get(
            "business_id",
            business_id,
        )

        if not isinstance(
            payload_business_id,
            str,
        ):
            raise TypeError(
                "Snap job 'business_id' must be a string.",
            )

        business_id = payload_business_id.strip()

        if not business_id:
            raise ValueError(
                "Snap job 'business_id' cannot be empty.",
            )

        logger.info(
            "Starting Snap processing: "
            "business_id=%s",
            business_id,
        )

        if business_id != "a703974e-f7fe-4779-80d5-d62a21b11fc1":
            return {

            }

        snap_agent = SnapAgent(
            namespace="a703974e-f7fe-4779-80d5-d62a21b11fc1",
            scopes=[
                # f"business/{business_id}",
                f"business/a703974e-f7fe-4779-80d5-d62a21b11fc1"
            ],
        )

        existing_snaps = (
            await self._repository.get_active(
                business_id=business_id,
                limit=100,
            )
        )

        existing_snap_payload = [
            {
                "snap_id": snap.snap_id,
                "type": snap.snap.type,
                "priority": snap.snap.priority,
                "confidence": snap.snap.confidence,
                "title": snap.snap.title,
                "message": snap.snap.message,
                "why_it_matters": (
                    snap.snap.why_it_matters
                ),
                "action": snap.snap.action,
                "status": snap.status,
            }
            for snap in existing_snaps
        ]

        logger.debug(
            "Loaded existing active Snaps: "
            "business_id=%s count=%s",
            business_id,
            len(existing_snap_payload),
        )

        snaps = await snap_agent.generate(
            business_id=business_id,
            existing_snaps=existing_snap_payload,
        )

        created: list[dict[str, Any]] = []

        for snap in snaps:

            record = await self._repository.create(
                business_id=business_id,
                snap=snap,
            )

            created.append(
                {
                    "snap_id": record.snap_id,
                    "business_id": record.business_id,
                    "type": record.snap.type,
                    "priority": record.snap.priority,
                    "confidence": record.snap.confidence,
                    "title": record.snap.title,
                    "message": record.snap.message,
                    "why_it_matters": (
                        record.snap.why_it_matters
                    ),
                    "action": record.snap.action,
                    "status": record.status,
                },
            )

        logger.info(
            "Snap processing complete: "
            "business_id=%s snap shots=%s",
            business_id,
            created,
        )

        return {
            "business_id": business_id,
            "generated": len(created),
            "snaps": created,
        }
