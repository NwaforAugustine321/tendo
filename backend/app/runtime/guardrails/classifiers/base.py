from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.guardrails.result import SafetyResult


class SafetyClassifier(ABC):

    @abstractmethod
    async def classify(
        self,
        text: str,
    ) -> SafetyResult:
        ...
