from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BusinessObject(ABC):

    @property
    @abstractmethod
    def object_type(self) -> str:
        ...

    @abstractmethod
    def attributes(self) -> dict[str, Any]:
        ...
