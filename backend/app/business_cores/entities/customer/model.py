from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.object import BusinessObject


@dataclass
class Customer(BusinessObject):
    id: str | None
    business_id: str
    data: dict[str, Any] = field(default_factory=dict)
    status: str = "active"

    @property
    def object_type(self) -> str:
        return "customer"

    def attributes(self) -> dict[str, Any]:
        return dict(self.data)
