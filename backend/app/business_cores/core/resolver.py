from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .identity import IdentityStrategy
from .repository import BusinessObjectRepository


@dataclass(frozen=True)
class ResolutionResult:
    object_id: str
    created: bool
    status: str


class BusinessObjectResolver:

    def __init__(
        self,
        *,
        repository: BusinessObjectRepository,
        identity_strategy: IdentityStrategy,
        object_type: str,
    ) -> None:
        self.repository = repository
        self.identity_strategy = identity_strategy
        self.object_type = object_type

        strategy_object_type = getattr(
            identity_strategy,
            "object_type",
            None,
        )

        if (
            strategy_object_type is not None
            and strategy_object_type != object_type
        ):
            raise ValueError(
                "Identity strategy object type does not match "
                f"resolver object type: "
                f"{strategy_object_type!r} != {object_type!r}"
            )

    async def resolve(
        self,
        *,
        business_id: str,
        data: dict[str, Any],
    ) -> ResolutionResult:

        identities = self.identity_strategy.build_identities(
            business_id=business_id,
            data=data,
        )

        result = await self.repository.resolve(
            business_id=business_id,
            object_type=self.object_type,
            data=data,
            identities=identities,
        )

        return ResolutionResult(
            object_id=str(result["id"]),
            created=bool(result["created"]),
            status=result.get("status", "active"),
        )

    async def update(
        self,
        *,
        business_id: str,
        object_id: str,
        data: dict[str, Any],
    ) -> ResolutionResult:

        identities = self.identity_strategy.build_identities(
            business_id=business_id,
            data=data,
        )

        result = await self.repository.update(
            business_id=business_id,
            object_type=self.object_type,
            object_id=object_id,
            data=data,
            identities=identities,
        )

        return ResolutionResult(
            object_id=str(result["id"]),
            created=False,
            status=result.get("status", "active"),
        )

    async def get(
        self,
        *,
        business_id: str,
        object_id: str,
    ) -> dict[str, Any] | None:

        return await self.repository.get(
            business_id=business_id,
            object_type=self.object_type,
            object_id=object_id,
        )

    async def delete(
        self,
        *,
        business_id: str,
        object_id: str,
    ) -> bool:

        return await self.repository.delete(
            business_id=business_id,
            object_type=self.object_type,
            object_id=object_id,
        )

    async def list(
        self,
        *,
        business_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        return await self.repository.list(
            business_id=business_id,
            object_type=self.object_type,
            limit=limit,
            offset=offset,
        )
