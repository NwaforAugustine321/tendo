from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.db.client import get_client


class LearningEventRPCI(ABC):

    # ==========================================================
    # Event discovery
    # ==========================================================

    @abstractmethod
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
        """
        Fetch the next events after the committed
        business event sequence cursor.
        """
        raise NotImplementedError

    # ==========================================================
    # Next document
    # ==========================================================

    @abstractmethod
    async def fetch_next_document(
        self,
        *,
        business_id: str,
        cursor: int | None,
    ) -> list[dict[str, Any]]:
        """
        Fetch the next document that must be processed.

        The document is determined by the first business event
        after the committed cursor.

        All chunks belonging to that document are returned in
        chunk_index order.

        This guarantees that BLA finishes one document before
        moving to another document.
        """
        raise NotImplementedError

    # ==========================================================
    # Document chunks
    # ==========================================================

    @abstractmethod
    async def fetch_document_chunks(
        self,
        *,
        business_id: str,
        document_key: str,
        after_chunk_index: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch chunks belonging to one document.

        Chunks are returned in chunk_index order.

        after_chunk_index allows processing to resume from
        a checkpoint.
        """
        raise NotImplementedError

    # ==========================================================
    # Cursor
    # ==========================================================

    @abstractmethod
    async def get_cursor(
        self,
        *,
        business_id: str,
    ) -> int | None:
        """
        Return the last successfully committed
        business event sequence_id.
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
        Commit the last successfully processed
        business event sequence_id.
        """
        raise NotImplementedError

    # ==========================================================
    # Checkpoint
    # ==========================================================

    @abstractmethod
    async def get_checkpoint(
        self,
        *,
        business_id: str,
        document_key: str,
    ) -> dict[str, Any] | None:
        """
        Return the current in-progress document checkpoint.
        """
        raise NotImplementedError

    @abstractmethod
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
        """
        Save the progress of an in-progress document.

        This is called after a chunk has been successfully
        incorporated into the accumulated learning context.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_checkpoint(
        self,
        *,
        business_id: str,
        document_key: str,
    ) -> None:
        """
        Remove the checkpoint after the complete document
        has been successfully processed and committed.
        """
        raise NotImplementedError

    # ==========================================================
    # Businesses
    # ==========================================================

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

    CURSOR_TABLE = "bla_cursors"

    EVENT_TABLE = "business_events"

    CHECKPOINT_TABLE = "bla_checkpoints"

    BUSINESS_TABLE = "business_profiles"

    def __init__(
        self,
    ) -> None:

        self._db = get_client()

    # ==========================================================
    # Event discovery
    # ==========================================================

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

        business_id = self._validate_business_id(
            business_id,
        )

        cursor = self._validate_cursor(
            cursor,
        )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero.",
            )

        query = (
            self._db
            .table(
                self.EVENT_TABLE,
            )
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

        # Supabase client is synchronous.
        response = query.execute()

        events = response.data or []

        if not events:

            return [], cursor

        next_cursor = int(
            events[-1]["sequence_id"],
        )

        return events, next_cursor

    # ==========================================================
    # Next document
    # ==========================================================

    async def fetch_next_document(
        self,
        *,
        business_id: str,
        cursor: int | None,
    ) -> list[dict[str, Any]]:

        business_id = self._validate_business_id(
            business_id,
        )

        cursor = self._validate_cursor(
            cursor,
        )

        # ------------------------------------------------------
        # First find the first event after the committed cursor.
        #
        # This is important because sequence_id defines the
        # global processing order for a business.
        # ------------------------------------------------------

        query = (
            self._db
            .table(
                self.EVENT_TABLE,
            )
            .select("*")
            .eq(
                "business_id",
                business_id,
            )
            .order(
                "sequence_id",
                desc=False,
            )
            .limit(1)
        )

        if cursor is not None:

            query = query.gt(
                "sequence_id",
                cursor,
            )

        response = query.execute()

        events = response.data or []

        if not events:

            return []

        first_event = events[0]

        document_key = first_event.get(
            "document_key",
        )

        # ------------------------------------------------------
        # Non-document event.
        #
        # Return the event itself so the service can process
        # ordinary business events as a single item.
        # ------------------------------------------------------

        if not document_key:

            return [
                first_event,
            ]

        document_key = self._validate_document_key(
            str(
                document_key,
            ),
        )

        # ------------------------------------------------------
        # Now fetch ONLY this document's chunks.
        #
        # We intentionally do not fetch chunks from subsequent
        # documents. This guarantees document ordering.
        # ------------------------------------------------------

        document_query = (
            self._db
            .table(
                self.EVENT_TABLE,
            )
            .select("*")
            .eq(
                "business_id",
                business_id,
            )
            .eq(
                "document_key",
                document_key,
            )
            .order(
                "chunk_index",
                desc=False,
            )
        )

        document_response = (
            document_query.execute()
        )

        return (
            document_response.data
            or []
        )

    # ==========================================================
    # Document chunks
    # ==========================================================

    async def fetch_document_chunks(
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

            if limit <= 0:
                raise ValueError(
                    "limit must be greater than zero.",
                )

        query = (
            self._db
            .table(
                self.EVENT_TABLE,
            )
            .select("*")
            .eq(
                "business_id",
                business_id,
            )
            .eq(
                "document_key",
                document_key,
            )
            .order(
                "chunk_index",
                desc=False,
            )
        )

        if after_chunk_index is not None:

            query = query.gt(
                "chunk_index",
                after_chunk_index,
            )

        if limit is not None:

            query = query.limit(
                limit,
            )

        response = query.execute()

        return response.data or []

    # ==========================================================
    # Cursor
    # ==========================================================

    async def get_cursor(
        self,
        *,
        business_id: str,
    ) -> int | None:

        business_id = self._validate_business_id(
            business_id,
        )

        response = (
            self._db
            .table(
                self.CURSOR_TABLE,
            )
            .select(
                "cursor, status",
            )
            .eq(
                "business_id",
                business_id,
            )
            .maybe_single()
            .execute()
        )

        if not response or not response.data:

            return None

        # Only return cursor if the last operation completed
        if response.data.get("status") == "processing":
            # Return the cursor value anyway — the checkpoint system
            # handles resuming mid-document
            pass

        cursor = response.data.get(
            "cursor",
        )

        if cursor is None:

            return None

        return int(
            cursor,
        )

    async def commit_cursor(
        self,
        *,
        business_id: str,
        cursor: int,
    ) -> None:

        business_id = self._validate_business_id(
            business_id,
        )

        cursor = self._validate_required_cursor(
            cursor,
        )

        (
            self._db
            .table(
                self.CURSOR_TABLE,
            )
            .upsert(
                {
                    "business_id": business_id,
                    "cursor": cursor,
                    "status": "completed",
                },
                on_conflict="business_id",
            )
            .execute()
        )

    async def mark_cursor_processing(
        self,
        *,
        business_id: str,
        cursor: int,
    ) -> None:

        business_id = self._validate_business_id(
            business_id,
        )

        cursor = self._validate_required_cursor(
            cursor,
        )

        (
            self._db
            .table(
                self.CURSOR_TABLE,
            )
            .upsert(
                {
                    "business_id": business_id,
                    "cursor": cursor,
                    "status": "processing",
                },
                on_conflict="business_id",
            )
            .execute()
        )

    # ==========================================================
    # Checkpoint
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

        response = (
            self._db
            .table(
                self.CHECKPOINT_TABLE,
            )
            .select("*")
            .eq(
                "business_id",
                business_id,
            )
            .eq(
                "document_key",
                document_key,
            )
            .maybe_single()
            .execute()
        )

        if not response or not response.data:

            return None

        return response.data

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

        last_sequence_id = (
            self._validate_required_cursor(
                last_sequence_id,
            )
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

        if last_chunk_index > total_chunks:
            raise ValueError(
                "last_chunk_index must not exceed "
                "total_chunks.",
            )

        (
            self._db
            .table(
                self.CHECKPOINT_TABLE,
            )
            .upsert(
                {
                    "business_id": business_id,
                    "document_key": document_key,
                    "last_chunk_index": last_chunk_index,
                    "last_sequence_id": last_sequence_id,
                    "accumulated_payload": accumulated_payload,
                    "total_chunks": total_chunks,
                },
                on_conflict=(
                    "business_id,document_key"
                ),
            )
            .execute()
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

        (
            self._db
            .table(
                self.CHECKPOINT_TABLE,
            )
            .delete()
            .eq(
                "business_id",
                business_id,
            )
            .eq(
                "document_key",
                document_key,
            )
            .execute()
        )

    # ==========================================================
    # Businesses
    # ==========================================================

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

        response = (
            self._db
            .table(
                self.BUSINESS_TABLE,
            )
            .select(
                "id",
            )
            .order(
                "id",
                desc=False,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return [
            str(
                row["id"],
            )
            for row in (
                response.data or []
            )
            if row.get("id") is not None
        ]

    # ==========================================================
    # Validation helpers
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

    @staticmethod
    def _validate_cursor(
        cursor: int | None,
    ) -> int | None:

        if cursor is None:

            return None

        if not isinstance(
            cursor,
            int,
        ):
            raise TypeError(
                "cursor must be an integer or None.",
            )

        if cursor < 0:

            raise ValueError(
                "cursor cannot be negative.",
            )

        return cursor

    @staticmethod
    def _validate_required_cursor(
        cursor: int,
    ) -> int:

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

        return cursor
