from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..interfaces import (
    BackgroundJobRPC,
    IntervalUnit,
)
from ..worker import BackgroundWorker

from ...runtime.agent_hub.bla.agent import (
    BusinessLearningAgent,
)


logger = logging.getLogger(__name__)


class BLABackgroundWorker(
    BackgroundWorker,
):
    """
    Background worker for Business Learning Agent jobs.
    """

    def __init__(
        self,
        *,
        rpc: BackgroundJobRPC,
    ) -> None:

        super().__init__(
            job_type="bla",
            worker_name="bla",
        )

        if rpc is None:
            raise ValueError(
                "'rpc' instance not found.",
            )

        self._rpc = rpc

        self._bla = BusinessLearningAgent()

        self._event = (
            self._bla
            .learning_service
            .event
        )

        task = asyncio.create_task(
            self._initialize_business_bla_jobs(
                page_size=100,
                batch_size=30,
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
                "BLA job initialization failed: %s",
                exc,
                exc_info=exc,
            )

    @property
    def bla(
        self,
    ) -> BusinessLearningAgent:
        """
        Return the Business Learning Agent.
        """

        return self._bla

    async def _initialize_business_bla_jobs(
        self,
        *,
        page_size: int,
        batch_size: int,
    ) -> int:
        """
        Discover businesses using pagination and create
        recurring BLA jobs for them.
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

                if not isinstance(
                    business_id,
                    str,
                ):
                    continue

                business_id = (
                    business_id.strip()
                )

                if not business_id:
                    continue

                # await self._rpc.enqueue(
                #     job_type=self.job_type,
                #     id=business_id,
                #     payload={
                #         "business_id": business_id,
                #         "batch_size": batch_size,
                #     },
                #     interval_value=12,
                #     interval_unit=IntervalUnit.HOURS,
                # )

                total += 1

            if len(
                business_ids,
            ) < page_size:
                break

            offset += page_size

        logger.info(
            "BLA job initialization complete: "
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
                "BLA job requires 'id'.",
            )

        if not isinstance(
            job_id,
            str,
        ):
            raise TypeError(
                "BLA job 'id' must be a string.",
            )

        job_id = job_id.strip()

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

        if not isinstance(
            batch_size,
            int,
        ):
            raise TypeError(
                "BLA job 'batch_size' must be an integer.",
            )

        if batch_size <= 0:
            raise ValueError(
                "BLA job 'batch_size' must be greater than zero.",
            )

        logger.info(
            "Starting BLA processing: "
            "business_id=%s batch_size=%s",
            job_id,
            batch_size,
        )

        result = await self._bla.learn(
            business_id=job_id,
            batch_size=batch_size,
        )

        logger.info(
            "BLA processing completed: "
            "business_id=%s "
            "learned respond=%s",
            job_id,
            str(result.knowledge)
        )

        if hasattr(
            result,
            "model_dump",
        ):

            return result.model_dump()

        return {
            "knowledge": result.knowledge,
        }
