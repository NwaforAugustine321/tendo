from __future__ import annotations

from typing import Any

from .rpc import (
    LearningEventRPC,
    LearningEventRPCI,
)


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

    # ==========================================================
    # Business pagination
    # ==========================================================

    async def get_business_ids(
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

        return await self._rpc.fetch_business_ids(
            offset=offset,
            limit=limit,
        )

    # ==========================================================
    # Event cursor
    # ==========================================================

    async def get_cursor(
        self,
        *,
        business_id: str,
    ) -> int | None:

        business_id = self._validate_business_id(
            business_id,
        )

        return await self._rpc.get_cursor(
            business_id=business_id,
        )

    async def commit(
        self,
        *,
        business_id: str,
        cursor: int,
    ) -> None:

        business_id = self._validate_business_id(
            business_id,
        )

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

        await self._rpc.commit_cursor(
            business_id=business_id,
            cursor=cursor,
        )

    # ==========================================================
    # Event batches
    # ==========================================================

    async def get_batch(
        self,
        *,
        business_id: str,
        limit: int,
    ) -> tuple[
        list[dict[str, Any]],
        int | None,
    ]:

        business_id = self._validate_business_id(
            business_id,
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

    # ==========================================================
    # Next complete document
    # ==========================================================

    async def get_next_documents(
        self,
        *,
        business_id: str,
    ) -> list[dict[str, Any]]:

        business_id = self._validate_business_id(
            business_id,
        )

        cursor = await self._rpc.get_cursor(
            business_id=business_id,
        )

        return await self._rpc.fetch_next_document(
            business_id=business_id,
            cursor=cursor,
        )

    # ==========================================================
    # Document chunks
    # ==========================================================

    async def get_document_chunks(
        self,
        *,
        business_id: str,
        document_key: str,
        after_chunk_index: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:

        business_id = self._validate_business_id(
            business_id,
        )

        document_key = self._validate_document_key(
            document_key,
        )

        if after_chunk_index is not None:

            if not isinstance(
                after_chunk_index,
                int,
            ):
                raise TypeError(
                    "after_chunk_index must be "
                    "an integer or None.",
                )

            if after_chunk_index < -1:
                raise ValueError(
                    "after_chunk_index cannot be "
                    "less than -1.",
                )

        if limit is not None:

            if not isinstance(
                limit,
                int,
            ):
                raise TypeError(
                    "limit must be an integer or None.",
                )

            if limit <= 0:
                raise ValueError(
                    "limit must be greater than zero.",
                )

        return await self._rpc.fetch_document_chunks(
            business_id=business_id,
            document_key=document_key,
            after_chunk_index=after_chunk_index,
            limit=limit,
        )

    # ==========================================================
    # Document checkpoint
    # ==========================================================

    async def get_checkpoint(
        self,
        *,
        business_id: str,
        document_key: str,
    ) -> dict[str, Any] | None:

        business_id = self._validate_business_id(
            business_id,
        )

        document_key = self._validate_document_key(
            document_key,
        )

        return await self._rpc.get_checkpoint(
            business_id=business_id,
            document_key=document_key,
        )

    async def save_checkpoint(
        self,
        *,
        business_id: str,
        document_key: str,
        last_chunk_index: int,
        last_sequence_id: int,
        accumulated_payload: str,
        total_chunks: int,
    ) -> None:

        business_id = self._validate_business_id(
            business_id,
        )

        document_key = self._validate_document_key(
            document_key,
        )

        if not isinstance(
            last_chunk_index,
            int,
        ):
            raise TypeError(
                "last_chunk_index must be an integer.",
            )

        if last_chunk_index < 0:
            raise ValueError(
                "last_chunk_index cannot be negative.",
            )

        if not isinstance(
            last_sequence_id,
            int,
        ):
            raise TypeError(
                "last_sequence_id must be an integer.",
            )

        if last_sequence_id < 0:
            raise ValueError(
                "last_sequence_id cannot be negative.",
            )

        if not isinstance(
            accumulated_payload,
            str,
        ):
            raise TypeError(
                "accumulated_payload must be a string.",
            )

        if not accumulated_payload.strip():
            raise ValueError(
                "accumulated_payload cannot be empty.",
            )

        if not isinstance(
            total_chunks,
            int,
        ):
            raise TypeError(
                "total_chunks must be an integer.",
            )

        if total_chunks <= 0:
            raise ValueError(
                "total_chunks must be greater than zero.",
            )

        if last_chunk_index >= total_chunks:
            raise ValueError(
                "last_chunk_index must be less than "
                "total_chunks.",
            )

        await self._rpc.save_checkpoint(
            business_id=business_id,
            document_key=document_key,
            last_chunk_index=last_chunk_index,
            last_sequence_id=last_sequence_id,
            accumulated_payload=accumulated_payload,
            total_chunks=total_chunks,
        )

    async def delete_checkpoint(
        self,
        *,
        business_id: str,
        document_key: str,
    ) -> None:

        business_id = self._validate_business_id(
            business_id,
        )

        document_key = self._validate_document_key(
            document_key,
        )

        await self._rpc.delete_checkpoint(
            business_id=business_id,
            document_key=document_key,
        )

    # ==========================================================
    # Validation
    # ==========================================================

    @staticmethod
    def _validate_business_id(
        business_id: str,
    ) -> str:

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

        return business_id

    @staticmethod
    def _validate_document_key(
        document_key: str,
    ) -> str:

        if not isinstance(
            document_key,
            str,
        ):
            raise TypeError(
                "document_key must be a string.",
            )

        document_key = document_key.strip()

        if not document_key:
            raise ValueError(
                "document_key cannot be empty.",
            )

        return document_key
