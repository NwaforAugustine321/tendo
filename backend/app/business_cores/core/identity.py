from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Identity:
    object_type: str
    identifier_type: str
    identifier_key: str
    identifier_hash: str


@dataclass(frozen=True)
class IdentityField:
    name: str
    normalizer: Callable[[Any], str | None]


class IdentityStrategy(ABC):

    @property
    @abstractmethod
    def identity_fields(self) -> tuple[IdentityField, ...]:
        ...

    @abstractmethod
    def build_identities(
        self,
        *,
        business_id: str,
        data: dict[str, Any],
    ) -> list[Identity]:
        ...


class ConfigIdentityStrategy(IdentityStrategy):

    def __init__(
        self,
        *,
        object_type: str,
        fields: tuple[IdentityField, ...],
    ) -> None:
        self.object_type = object_type
        self._identity_fields = fields

    @property
    def identity_fields(
        self,
    ) -> tuple[IdentityField, ...]:
        return self._identity_fields

    def build_identities(
        self,
        *,
        business_id: str,
        data: dict[str, Any],
    ) -> list[Identity]:

        identities: list[Identity] = []

        for field in self._identity_fields:
            value = data.get(field.name)

            normalized_value = field.normalizer(value)

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


class IdentityHasher:

    @staticmethod
    def hash(
        value: str,
    ) -> str:

        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()


def build_identity_hash(
    *,
    business_id: str,
    object_type: str,
    identifier_type: str,
    identifier_value: str,
) -> str:

    key = "|".join(
        (
            business_id,
            object_type,
            identifier_type,
            identifier_value,
        )
    )

    return IdentityHasher.hash(key)


def normalize_identity_value(
    value: Any,
) -> str | None:

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip().lower()
    else:
        value = str(value).strip().lower()

    return value or None


def normalize_identity_email(
    value: Any,
) -> str | None:

    if not isinstance(value, str):
        return None

    value = value.strip().lower()

    return value or None


def normalize_identity_phone(
    value: Any,
) -> str | None:

    if not isinstance(value, str):
        return None

    value = value.strip()

    return value or None
