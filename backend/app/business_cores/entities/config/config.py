from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EntityFieldConfig:
    name: str
    type: str = "string"
    required: bool = False
    identity: bool = False
    description: str = ""
    aliases: tuple[str, ...] = ()
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityAgentConfig:
    agent_name: str
    enabled: bool = True
    instructions: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityConfig:
    object_type: str
    enabled: bool = True
    fields: tuple[EntityFieldConfig, ...] = ()
    agent: EntityAgentConfig | None = None
    config: dict[str, Any] = field(default_factory=dict)

    def get_field(
        self,
        name: str,
    ) -> EntityFieldConfig | None:

        for field_config in self.fields:
            if field_config.name == name:
                return field_config

        return None

    def has_field(
        self,
        name: str,
    ) -> bool:
        return self.get_field(name) is not None

    def field_names(self) -> tuple[str, ...]:
        return tuple(
            field_config.name
            for field_config in self.fields
        )

    def required_fields(
        self,
    ) -> tuple[EntityFieldConfig, ...]:

        return tuple(
            field_config
            for field_config in self.fields
            if field_config.required
        )

    def required_field_names(self) -> tuple[str, ...]:
        return tuple(
            field_config.name
            for field_config in self.required_fields()
        )

    def identity_fields(
        self,
    ) -> tuple[EntityFieldConfig, ...]:

        return tuple(
            field_config
            for field_config in self.fields
            if field_config.identity
        )

    def identity_field_names(self) -> tuple[str, ...]:
        return tuple(
            field_config.name
            for field_config in self.identity_fields()
        )

    def is_agent_enabled(self) -> bool:
        return (
            self.enabled
            and self.agent is not None
            and self.agent.enabled
        )

    def validate_data(
        self,
        data: dict[str, Any],
    ) -> None:

        if not self.enabled:
            raise ValueError(
                f"Entity is disabled: {self.object_type}"
            )

        missing_fields = [
            field_config.name
            for field_config in self.required_fields()
            if data.get(field_config.name) is None
        ]

        if missing_fields:
            raise ValueError(
                f"Missing required fields for "
                f"{self.object_type}: "
                f"{', '.join(missing_fields)}"
            )

    def filter_data(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        allowed_fields = set(
            self.field_names()
        )

        return {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }
