from __future__ import annotations

from abc import ABC, abstractmethod


class PromptLeakageDetectionStrategy(ABC):
    """
    Common interface for prompt leakage detection strategies.

    """

    @abstractmethod
    async def detect(
        self,
        text: str,
    ) -> dict | None:
        """
        Detect prompt leakage in the provided text.

        Args:
            text: LLM-generated content to inspect.

        Returns:
            Detection source identifier, or an empty string when safe.
        """

        raise NotImplementedError
