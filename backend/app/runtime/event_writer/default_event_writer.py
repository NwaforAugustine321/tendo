from __future__ import annotations

from app.db.client import get_client

from .event_writer import EventWriterI
from supabase import Client


class EventWriter(
    EventWriterI,
):
    """
    Event writer.
    """

    def __init__(self, db: Client) -> None:
        self._db = db

    async def write_chunk(
        self,
        *,
        business_id: str,
        event_type: str,
        document_key: str,
        chunk_index: int,
        total_chunks: int,
        payload: str,
    ) -> None:

        try:

            if not business_id.strip():
                raise ValueError(
                    "business  id cannot be empty.",
                )

            if not event_type.strip():
                raise ValueError(
                    "event_type cannot be empty.",
                )

            if not document_key.strip():
                raise ValueError(
                    "document_key cannot be empty.",
                )

            if chunk_index < 0:
                raise ValueError(
                    "chunk_index cannot be negative.",
                )

            if total_chunks <= 0:
                raise ValueError(
                    "total_chunks must be greater than zero.",
                )

            if chunk_index >= total_chunks:
                raise ValueError(
                    "chunk_index must be less than total_chunks.",
                )

            if not isinstance(payload, str):
                raise TypeError(
                    "payload must be a string.",
                )

            if not payload.strip():
                raise ValueError(
                    "payload cannot be empty.",
                )

                self._db.table("business_events")\
                    .insert(
                    {
                        "business_id": business_id,
                        "event_type": event_type,
                        "document_key": document_key,
                        "chunk_index": chunk_index,
                        "total_chunks": total_chunks,
                        "payload": payload,
                    }
                ).execute()

        except Exception as e:
            raise e
