from __future__ import annotations

from .config.config import (
    EntityAgentConfig,
    EntityConfig,
    EntityFieldConfig,
)


DEFAULT_CUSTOMER_CONFIG = EntityConfig(
    object_type="customer",
    enabled=True,
    agent=EntityAgentConfig(
        agent_name="customer",
    ),
    fields=(
        EntityFieldConfig(
            name="name",
            type="string",
            description="Customer full name",
        ),
        EntityFieldConfig(
            name="email",
            type="email",
            identity=True,
            description="Customer email address",
        ),
        EntityFieldConfig(
            name="phone",
            type="phone",
            identity=True,
            description="Customer phone number",
        ),
        EntityFieldConfig(
            name="external_customer_id",
            type="string",
            identity=True,
            description="External customer identifier",
        ),
    ),
)


DEFAULT_TRANSACTION_CONFIG = EntityConfig(
    object_type="transaction",
    enabled=True,
    agent=EntityAgentConfig(
        agent_name="transaction",
    ),
    fields=(
        EntityFieldConfig(
            name="amount",
            type="number",
            description="Transaction amount",
        ),
        EntityFieldConfig(
            name="currency",
            type="string",
            description="Transaction currency",
        ),
        EntityFieldConfig(
            name="transaction_date",
            type="datetime",
            description="Date and time of transaction",
        ),
        EntityFieldConfig(
            name="description",
            type="string",
            description="Transaction description",
        ),
        EntityFieldConfig(
            name="external_transaction_id",
            type="string",
            identity=True,
            description="External transaction identifier",
        ),
    ),
)


DEFAULT_ENTITY_CONFIGS: dict[str, EntityConfig] = {
    config.object_type: config
    for config in (
        DEFAULT_CUSTOMER_CONFIG,
        DEFAULT_TRANSACTION_CONFIG,
    )
}


def get_default_entity_config(
    object_type: str,
) -> EntityConfig | None:

    return DEFAULT_ENTITY_CONFIGS.get(
        object_type,
    )
