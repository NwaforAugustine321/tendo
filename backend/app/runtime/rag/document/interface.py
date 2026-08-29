from __future__ import annotations

from abc import ABC, abstractmethod

from .models import ProcessingResult, RecordContentInput


class ContentProcessor(ABC):
    """
    Interface for processing record/document content.

    Implementations are responsible only for content processing.
    Event persistence and other side effects are handled separately.
    """

    @abstractmethod
    async def process(
        self,
        record_content: RecordContentInput,
    ) -> ProcessingResult:
        """
        Process the supplied record content.

        Args:
            record_content:
                Content and metadata required for processing.

        Returns:
            ProcessingResult containing the processing outcome.
        """
        raise NotImplementedError
