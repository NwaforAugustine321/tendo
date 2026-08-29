from __future__ import annotations

from .config.config import EntityConfig
from ..core.identity import (
    ConfigIdentityStrategy,
    IdentityField,
    normalize_identity_email,
    normalize_identity_phone,
    normalize_identity_value,
)


def build_identity_strategy(
    config: EntityConfig,
) -> ConfigIdentityStrategy:

    fields: list[IdentityField] = []

    for field in config.identity_fields():
        if field.type == "email":
            normalizer = normalize_identity_email

        elif field.type == "phone":
            normalizer = normalize_identity_phone

        else:
            normalizer = normalize_identity_value

        fields.append(
            IdentityField(
                name=field.name,
                normalizer=normalizer,
            )
        )

    return ConfigIdentityStrategy(
        object_type=config.object_type,
        fields=tuple(fields),
    )
