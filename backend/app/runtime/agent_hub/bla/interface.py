from __future__ import annotations

from abc import ABC, abstractmethod


from abc import ABC, abstractmethod


class LearningKnowledge(ABC):

    @abstractmethod
    async def save_knowledge(
        self,
        *,
        knowledge: list[str],
    ) -> None:
        raise NotImplementedError


class LearningAgent(ABC):
    """
    Interface for a long-term learning agent.

    The interface defines the learning operation without
    coupling it to the background-job infrastructure.
    """

    @abstractmethod
    async def learn(
        self,
        *,
        business_id: str,
    ) -> str:
        """
        Run one learning cycle for a business.

        Args:
            business_id:
                Identifier of the business whose accumulated
                events and knowledge are being learned.

        Returns:
            Durable learned knowledge produced during
            the learning cycle.
        """
        raise NotImplementedError
