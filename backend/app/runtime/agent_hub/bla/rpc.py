from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.db.client import get_client


class LearningEventRPCI(ABC):

    @abstractmethod
    async def fetch_events(
        self,
        *,
        business_id: str,
        cursor: int | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int | None]:
        """
        Fetch the next batch of events after the sequence cursor.

        The cursor represents the last successfully processed
        event sequence_id.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_cursor(
        self,
        *,
        business_id: str,
    ) -> int | None:
        """
        Return the last successfully committed event sequence.
        """
        raise NotImplementedError

    @abstractmethod
    async def commit_cursor(
        self,
        *,
        business_id: str,
        cursor: int,
    ) -> None:
        """
        Commit the event sequence after the corresponding learning
        operation has been successfully persisted.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_business_ids(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[str]:
        """
        Fetch business IDs using offset/limit pagination.
        """
        raise NotImplementedError


class LearningEventRPC(
    LearningEventRPCI,
):

    def __init__(
        self,
    ) -> None:

        self._db = get_client()

    async def fetch_events(
        self,
        *,
        business_id: str,
        cursor: int | None,
        limit: int,
    ) -> tuple[
        list[dict[str, Any]],
        int | None,
    ]:

        if not isinstance(
            business_id,
            str,
        ):
            raise TypeError(
                "business_id must be a string.",
            )

        business_id = business_id.strip()

        if not business_id:
            raise ValueError(
                "business_id cannot be empty.",
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        query = (
            self._db
            .table("business_events")
            .select("*")
            .eq(
                "business_id",
                business_id,
            )
            .order(
                "sequence_id",
                desc=False,
            )
            .limit(
                limit,
            )
        )

        if cursor is not None:
            query = query.gt(
                "sequence_id",
                cursor,
            )

        response = query.execute()

        events = response.data or []

        if not events:
            return [], cursor

        next_cursor = int(
            events[-1]["sequence_id"],
        )

        return events, next_cursor

    async def get_cursor(
        self,
        *,
        business_id: str,
    ) -> int | None:

        response = self._db\
            .table("bla_cursors")\
            .select("cursor")\
            .eq(
                "business_id",
                business_id,
            )\
            .maybe_single()\
            .execute()

        if not response or not response.data:
            return None

        cursor = response.data.get(
            "cursor",
        )

        if cursor is None:
            return None

        return int(cursor)

    async def commit_cursor(
        self,
        *,
        business_id: str,
        cursor: int,
    ) -> None:

        if not isinstance(
            cursor,
            int,
        ):
            raise TypeError(
                "cursor must be an integer.",
            )

        if cursor < 0:
            raise ValueError(
                "cursor cannot be negative.",
            )

            self._db\
                .table("bla_cursors")\
                .upsert(
                    {
                        "business_id": business_id,
                        "cursor": cursor,
                    },
                    on_conflict="business_id",
                )\
                .execute()

    async def fetch_business_ids(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[str]:

        if offset < 0:
            raise ValueError(
                "offset cannot be negative.",
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        response = self._db\
            .table("business_profiles")\
            .select("id")\
            .order(
                "id",
            )\
            .range(
                offset,
                offset + limit - 1,
            )\
            .execute()

        return [
            str(row["id"])
            for row in (response.data or [])
            if row.get("id") is not None
        ]
