from __future__ import annotations

from typing import Any

from ..worker import BackgroundWorker

from ...runtime.agent_hub.bla.agent import BusinessLearningAgent


class BLABackgroundWorker(
    BackgroundWorker,
):

    def __init__(
        self,
    ) -> None:

        super().__init__(
            job_type="bla_learning",
            worker_name="bla",
        )

        self._bla = BusinessLearningAgent()

    @property
    def bla(self) -> BusinessLearningAgent:
        return self._bla

    @property
    def job_type(self) -> str:
        return "bla_learning"

    @property
    def worker_name(self) -> str:
        return "bla"

    async def process(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any] | None:

        user_id = self.get_user_id(
            job,
        )

        if user_id is None:
            raise ValueError(
                "BLA job requires 'user_id'.",
            )

        user_id = user_id.strip()

        if not user_id:
            raise ValueError(
                "BLA job 'user_id' cannot be empty.",
            )

        payload = self.get_payload(
            job,
        )

        batch_size = payload.get('batch_size', None)

        result = await self._bla.learn(
            business_id=user_id,
            batch_size=batch_size
        )

        if hasattr(
            result,
            "model_dump",
        ):
            return result.model_dump()

        return {
            "knowledge": result.knowledge,
        }
