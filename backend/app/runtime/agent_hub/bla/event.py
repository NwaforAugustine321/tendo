from __future__ import annotations

from typing import Any

from .rpc import LearningEventRPCI, LearningEventRPC


class LearningEvent:

    def __init__(
        self,
    ) -> None:

        self._rpc = LearningEventRPC()

    @property
    def rpc(
        self,
    ) -> LearningEventRPCI:
        return self._rpc

    async def get_business_ids(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[str]:

        return await self._rpc.fetch_business_ids(
            offset=offset,
            limit=limit,
        )

    async def get_batch(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> tuple[
        list[dict[str, Any]],
        str | None,
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

        cursor = await self._rpc.get_cursor(
            business_id=business_id,
        )

        return await self._rpc.fetch_events(
            business_id=business_id,
            cursor=cursor,
            limit=limit,
        )

    async def commit(
        self,
        *,
        business_id: str,
        cursor: str,
    ) -> None:

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

        if not isinstance(
            cursor,
            str,
        ):
            raise TypeError(
                "cursor must be a string.",
            )

        cursor = cursor.strip()

        if not cursor:
            raise ValueError(
                "cursor cannot be empty.",
            )

        await self._rpc.commit_cursor(
            business_id=business_id,
            cursor=cursor,
        )
