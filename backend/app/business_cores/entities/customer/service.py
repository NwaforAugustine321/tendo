from __future__ import annotations

from ...core.identity import IdentityStrategy
from ...core.resolver import BusinessObjectResolver
from .repository import CustomerRepository


class CustomerService(BusinessObjectResolver):

    def __init__(
        self,
        *,
        repository: CustomerRepository,
        identity_strategy: IdentityStrategy,
    ) -> None:
        super().__init__(
            repository=repository,
            identity_strategy=identity_strategy,
            object_type="customer",
        )
