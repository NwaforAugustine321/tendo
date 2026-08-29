from __future__ import annotations

from abc import ABC, abstractmethod


class EventWriterI(ABC):
    """
    Interface for writing  events.

    """

    @abstractmethod
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
        """
        Persist one document chunk as a business event.
        """
        raise NotImplementedError
