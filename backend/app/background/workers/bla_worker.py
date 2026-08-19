from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from ..interfaces import BackgroundJobRPC, IntervalUnit
from ..worker import BackgroundWorker

from ...runtime.agent_hub.bla.agent import BusinessLearningAgent
import logging
import time

logger = logging.getLogger(__name__)


class BLABackgroundWorker(
    BackgroundWorker,
):

    def __init__(
        self,
        *,
        rpc: BackgroundJobRPC,
    ) -> None:

        super().__init__(
            job_type="bla_learning",
            worker_name="bla",
        )

        self._rpc = rpc

        self._bla = BusinessLearningAgent()
        self._event = self._bla.learning_service.event

        task = asyncio.create_task(
            self._initialize_business_bla_jobs(page_size=1, batch_size=30)
        )
        task.add_done_callback(self._on_init_done)

    @staticmethod
    def _on_init_done(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error(
                "Initialization failed: %s", exc,
            )

    @property
    def bla(
        self,
    ) -> BusinessLearningAgent:
        return self._bla

    async def _initialize_business_bla_jobs(
        self,
        *,
        page_size: int,
        batch_size: int,
    ) -> int:
        """
        Discover all businesses using pagination and create
        recurring BLA jobs for them.

        Returns:
            Number of businesses processed.
        """

        if page_size <= 0:
            raise ValueError(
                "page_size must be greater than zero.",
            )

        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero.",
            )

        offset = 0
        total = 0

        while True:

            business_ids = (
                await self._event.get_business_ids(
                    offset=offset,
                    limit=page_size,
                )
            )

            if not business_ids:
                break

            for business_id in business_ids:

                logger.info(f'Enqueuing [Business BLA JOB]: {business_id}')

                business_id = business_id.strip()

                if not business_id:
                    continue

                await self._rpc.enqueue(
                    job_type=self.job_type,
                    id=business_id,
                    payload={
                        "business_id": business_id,
                        "batch_size": batch_size,
                    },
                    interval_value=2,
                    interval_unit=IntervalUnit.MINUTES

                )

                total += 1

            if len(business_ids) < page_size:
                break

            offset += page_size

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
                "BLA job requires 'id'.",
            )

        job_id = job_id .strip()

        if not job_id:
            raise ValueError(
                "BLA job 'id' cannot be empty.",
            )

        payload = self.get_payload(
            job,
        )

        batch_size = payload.get(
            "batch_size",
            10,
        )

        result = await self._bla.learn(
            business_id=job_id,
            batch_size=batch_size,
        )

        if hasattr(
            result,
            "model_dump",
        ):
            return result.model_dump()

        return {
            "knowledge": result.knowledge,
        }
