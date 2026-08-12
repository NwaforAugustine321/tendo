from abc import ABC, abstractmethod


class TokenCounter(ABC):

    @abstractmethod
    async def count(
        self,
        messages: list,
    ) -> int:
        ...
