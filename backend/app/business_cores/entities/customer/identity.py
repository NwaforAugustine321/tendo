from __future__ import annotations

from typing import Any

from ...core.identity import (
    Identity,
    IdentityField,
    IdentityStrategy,
    build_identity_hash,
)


class CustomerIdentityStrategy(IdentityStrategy):

    object_type = "customer"

    def __init__(
        self,
        *,
        identity_fields: tuple[IdentityField, ...] | None = None,
    ) -> None:
        self._identity_fields = (
            identity_fields
            if identity_fields is not None
            else self.default_identity_fields()
        )

    @property
    def identity_fields(
        self,
    ) -> tuple[IdentityField, ...]:
        return self._identity_fields

    @classmethod
    def default_identity_fields(
        cls,
    ) -> tuple[IdentityField, ...]:
        return (
            IdentityField(
                name="external_customer_id",
                normalizer=cls._normalize,
            ),
            IdentityField(
                name="email",
                normalizer=cls._normalize_email,
            ),
            IdentityField(
                name="phone",
                normalizer=cls._normalize_phone,
            ),
        )

    def build_identities(
        self,
        *,
        business_id: str,
        data: dict[str, Any],
    ) -> list[Identity]:

        identities: list[Identity] = []

        for field in self.identity_fields:
            normalized_value = field.normalizer(
                data.get(field.name)
            )

            if normalized_value is None:
                continue

            identities.append(
                self._build_identity(
                    business_id=business_id,
                    identifier_type=field.name,
                    identifier_value=normalized_value,
                )
            )

        return identities

    def _build_identity(
        self,
        *,
        business_id: str,
        identifier_type: str,
        identifier_value: str,
    ) -> Identity:

        return Identity(
            object_type=self.object_type,
            identifier_type=identifier_type,
            identifier_key=identifier_value,
            identifier_hash=build_identity_hash(
                business_id=business_id,
                object_type=self.object_type,
                identifier_type=identifier_type,
                identifier_value=identifier_value,
            ),
        )

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    @staticmethod
    def _normalize_email(
        value: Any,
    ) -> str | None:

        if not isinstance(value, str):
            return None

        value = value.strip().lower()

        return value or None

    @staticmethod
    def _normalize_phone(
        value: Any,
    ) -> str | None:

        if not isinstance(value, str):
            return None

        value = value.strip()

        return value or None
