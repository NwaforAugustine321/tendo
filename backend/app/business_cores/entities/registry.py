from __future__ import annotations

from ..core.resolver import BusinessObjectResolver
from .customer.identity import CustomerIdentityStrategy
from .customer.repository import CustomerRepository
from .customer.service import CustomerService
from .repository import EntityRepository


class EntityRegistry:

    def __init__(self) -> None:
        self._services: dict[str, BusinessObjectResolver] = {}
        self._repository = EntityRepository()

        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            object_type="customer",
            service=CustomerService(
                repository=CustomerRepository(
                    repository=self._repository,
                ),
                identity_strategy=CustomerIdentityStrategy(),
            ),
        )

    def register(
        self,
        *,
        object_type: str,
        service: BusinessObjectResolver,
    ) -> None:

        if not object_type:
            raise ValueError(
                "Entity object_type cannot be empty"
            )

        if object_type in self._services:
            raise ValueError(
                f"Entity already registered: {object_type}"
            )

        self._services[object_type] = service

    def get(
        self,
        object_type: str,
    ) -> BusinessObjectResolver:

        try:
            return self._services[object_type]
        except KeyError:
            raise ValueError(
                f"Unsupported business object type: {object_type}"
            ) from None

    def has(
        self,
        object_type: str,
    ) -> bool:
        return object_type in self._services

    def supported_types(
        self,
    ) -> tuple[str, ...]:
        return tuple(self._services.keys())

    @property
    def repository(self) -> EntityRepository:
        return self._repository


entity_registry = EntityRegistry()
