from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import LearningResult
from .event import LearningEvent
from .memory import LearningKnowledge, LearningKnowledgeMemory


class LearningService:

    def __init__(
        self,
    ) -> None:

        self._event = LearningEvent()

        self._knowledge = LearningKnowledgeMemory(namespace='', scopes=[])

    @property
    def event(self) -> LearningEvent:
        return self._event

    @property
    def knowledge(self) -> LearningKnowledge:
        return self._knowledge

    async def process(
        self,
        *,
        business_id: str,
        learn: Callable[
            [
                str,
                list[dict[str, Any]],
            ],
            Any,
        ],
        batch_size: int,
    ) -> LearningResult:

        business_id = business_id.strip()

        if not business_id:
            raise ValueError(
                "business_id cannot be empty.",
            )

        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero.",
            )

        information, cursor = (
            await self._event.get_batch(
                business_id=business_id,
                limit=batch_size,
            )
        )

        if not information:
            return LearningResult()

        result = await learn(
            business_id=business_id,
            information=information,
        )

        if not isinstance(
            result,
            LearningResult,
        ):
            raise TypeError(
                "learn must return LearningResult.",
            )

        if not result.knowledge:
            return result

        await self._knowledge.save_knowledge(
            knowledge=result.knowledge,
        )

        if cursor is not None:
            await self._event.commit(
                business_id=business_id,
                cursor=cursor,
            )

        return result
