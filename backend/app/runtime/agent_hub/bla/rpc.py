from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LearningEventRPC(ABC):

    @abstractmethod
    async def fetch_events(
        self,
        *,
        business_id: str,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        Fetch the next batch of events after the cursor.

        Returns:
            events:
                Events available for BLA processing.

            next_cursor:
                Cursor representing the last event in the batch.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_cursor(
        self,
        *,
        business_id: str,
    ) -> str | None:
        """
        Return the last successfully committed learning cursor.
        """
        raise NotImplementedError

    @abstractmethod
    async def commit_cursor(
        self,
        *,
        business_id: str,
        cursor: str,
    ) -> None:
        """
        Commit the cursor after the corresponding learning
        operation has been successfully persisted.
        """
        raise NotImplementedError


class EventRPC:

    def commit_cursor(business_id: str, cursor: str | None, limit: int,):
        pass

    def get_cursor(business_id: str):
        pass

    def fetch_events(business_id: str, cursor: str):
        pass
