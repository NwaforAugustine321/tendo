
from __future__ import annotations

import json

from typing import Any

from langchain_core.messages import AIMessage

from pydantic import BaseModel

from app.runtime.llm.response import (
    Interaction,
    InteractionType,
    LLMAction,
    LLMResponse,
    ToolCall,
)

from app.runtime.utils.tag_parser import extract_tag


class ResponseParser:

    def parse(
        self,
        *,
        provider_response: Any,
        output_type: type | None = None,
    ) -> LLMResponse:

        if not isinstance(
            provider_response,
            AIMessage,
        ):
            raise TypeError(
                "Unsupported provider response "
                f"'{type(provider_response).__name__}'."
            )

        print(
            "raw text from llm>>>",
            provider_response,
        )

        raw_text = self.extract_text(
            provider_response,
        )

        action = self.extract_action(
            raw_text,
        )

        content = self.extract_content(
            raw_text,
        )

        question = self.extract_question(
            raw_text,
        )

        interaction = self.extract_interaction(
            raw_text,
        )

        tool_calls = self.extract_tool_calls(
            provider_response,
        )

        parsed_action = self.parse_action(
            action,
        )

        parsed_interaction = self.parse_interaction(
            action=parsed_action,
            interaction=interaction,
            question=question,
        )

        user_text = self.resolve_text(
            raw_text=raw_text,
            content=content,
            action=parsed_action,
        )

        return LLMResponse(
            text=user_text,
            output=self.parse_output(
                provider_response=provider_response,
                output_type=output_type,
            ),
            tool_calls=tool_calls,
            metadata=self.extract_metadata(
                provider_response,
            ),
            raw=provider_response,
            action=parsed_action,
            content=user_text,
            interaction=parsed_interaction,
        )

    def resolve_text(
        self,
        *,
        raw_text: str,
        content: str | None,
        action: LLMAction | None,
    ) -> str:

        if action is None:
            return raw_text.strip()

        if content:
            return content.strip()

        return self.extract_text_outside_tags(
            raw_text,
        )

    def extract_text_outside_tags(
        self,
        text: str,
    ) -> str:

        cleaned = text

        for tag in (
            "action",
            "content",
            "question",
            "interaction",
        ):
            cleaned = self.remove_tag(
                cleaned,
                tag,
            )

        return cleaned.strip()

    def remove_tag(
        self,
        text: str,
        tag: str,
    ) -> str:

        import re

        pattern = re.compile(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            re.IGNORECASE | re.DOTALL,
        )

        return pattern.sub(
            "",
            text,
        )

    def parse_action(
        self,
        value: str | None,
    ) -> LLMAction | None:

        if not value:
            return None

        try:
            return LLMAction(
                value.strip().lower(),
            )
        except ValueError as error:
            raise ValueError(
                f"Unsupported LLM action '{value}'."
            ) from error

    def parse_interaction(
        self,
        *,
        action: LLMAction | None,
        interaction: str | None,
        question: str | None,
    ) -> Interaction | None:

        if action == LLMAction.REQUEST_CONFIRMATION:
            return Interaction(
                type=InteractionType.CONFIRMATION,
                question=question or "",
            )

        if action == LLMAction.REQUEST_APPROVAL:
            return Interaction(
                type=InteractionType.APPROVAL,
                question=question or "",
            )

        if not interaction:
            return None

        try:
            interaction_type = InteractionType(
                interaction.strip().lower(),
            )
        except ValueError as error:
            raise ValueError(
                f"Unsupported interaction type '{interaction}'."
            ) from error

        return Interaction(
            type=interaction_type,
            question=question or "",
        )

    def parse_output(
        self,
        *,
        provider_response: Any,
        output_type: type | None,
    ) -> Any:

        if output_type is None:
            return None

        if isinstance(
            provider_response,
            output_type,
        ):
            return provider_response

        if isinstance(
            provider_response,
            AIMessage,
        ):
            return self._parse_text(
                text=self.extract_text(
                    provider_response,
                ),
                output_type=output_type,
            )

        if isinstance(
            provider_response,
            dict,
        ):
            if (
                isinstance(
                    output_type,
                    type,
                )
                and issubclass(
                    output_type,
                    BaseModel,
                )
            ):
                return output_type.model_validate(
                    provider_response,
                )

            return provider_response

        raise TypeError(
            "Unsupported structured output "
            f"'{type(provider_response).__name__}'."
        )

    def extract_action(
        self,
        text: str,
    ) -> str | None:

        value = extract_tag(
            text,
            "action",
        ).strip()

        return value or None

    def extract_content(
        self,
        text: str,
    ) -> str | None:

        value = extract_tag(
            text,
            "content",
        ).strip()

        return value or None

    def extract_question(
        self,
        text: str,
    ) -> str | None:

        value = extract_tag(
            text,
            "question",
        ).strip()

        return value or None

    def extract_interaction(
        self,
        text: str,
    ) -> str | None:

        value = extract_tag(
            text,
            "interaction",
        ).strip()

        return value or None

    def extract_text(
        self,
        message: AIMessage,
    ) -> str:

        content = message.content

        if isinstance(
            content,
            str,
        ):
            return content

        if isinstance(
            content,
            list,
        ):
            parts: list[str] = []

            for item in content:

                if isinstance(
                    item,
                    str,
                ):
                    parts.append(
                        item,
                    )

                elif isinstance(
                    item,
                    dict,
                ):
                    parts.append(
                        str(
                            item.get(
                                "text",
                                "",
                            )
                        )
                    )

                else:
                    parts.append(
                        str(item)
                    )

            return "".join(
                parts,
            )

        return str(
            content,
        )

    def extract_metadata(
        self,
        message: AIMessage,
    ) -> dict[str, Any]:

        metadata: dict[str, Any] = {}

        for key, value in vars(
            message,
        ).items():

            if key.startswith(
                "_",
            ):
                continue

            if key in {
                "content",
                "tool_calls",
                "type",
            }:
                continue

            metadata[key] = value

        return metadata

    def extract_tool_calls(
        self,
        message: AIMessage,
    ) -> list[ToolCall]:

        tool_calls: list[ToolCall] = []

        for tool in getattr(
            message,
            "tool_calls",
            [],
        ):
            tool_calls.append(
                ToolCall(
                    id=tool.get(
                        "id",
                        "",
                    ),
                    name=tool.get(
                        "name",
                        "",
                    ),
                    arguments=tool.get(
                        "args",
                        {},
                    ),
                )
            )

        return tool_calls

    def _parse_text(
        self,
        *,
        text: str,
        output_type: type,
    ) -> Any:

        text = text.strip()

        if not text:
            return None

        if (
            isinstance(
                output_type,
                type,
            )
            and issubclass(
                output_type,
                BaseModel,
            )
        ):
            return output_type.model_validate_json(
                text,
            )

        try:
            return json.loads(
                text,
            )

        except json.JSONDecodeError as error:
            raise ValueError(
                "Model returned invalid JSON."
            ) from error
