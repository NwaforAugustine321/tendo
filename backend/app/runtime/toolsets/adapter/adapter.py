from abc import ABC, abstractmethod
from typing import Any


class ToolAdapter(ABC):

    @classmethod
    @abstractmethod
    def supports(cls, tool: Any) -> bool:
        """Return True if this adapter can wrap the object."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def id(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def args_schema(self):
        ...

    @abstractmethod
    def invoke(self, arguments: dict) -> Any:
        ...

    @abstractmethod
    async def ainvoke(self, arguments: dict) -> Any:
        ...
