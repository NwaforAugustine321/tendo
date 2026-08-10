
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.runtime.llm.response import LLMResponse, ToolCall


class ResponseParser:
    """
    Parses provider responses into a normalized LLMResponse.
    """

    def parse(
        self,
        *,
        provider_response: Any,
        output_type: type | None,
    ) -> LLMResponse:

        if not isinstance(provider_response, AIMessage):
            raise TypeError(
                f"Unsupported provider response "
                f"{type(provider_response).__name__}"
            )

        text = self.extract_text(
            provider_response,
        )

        return LLMResponse(
            text=text,
            output=self.parse_output(
                provider_response=provider_response,
                output_type=output_type,
            ),
            tool_calls=self.extract_tool_calls(
                provider_response,
            ),
            metadata=self.extract_metadata(
                provider_response,
            ),
            raw=provider_response,
        )

    def parse_output(
        self,
        *,
        provider_response: Any,
        output_type: type | None,
    ) -> Any:

        if output_type is None:
            return None

        #
        # Native structured output.
        #
        if isinstance(
            provider_response,
            output_type,
        ):
            return provider_response

        #
        # AIMessage
        #
        if isinstance(
            provider_response,
            AIMessage,
        ):
            return self._parse_text(
                self.extract_text(
                    provider_response,
                ),
                output_type,
            )

        #
        # Dictionary
        #
        if isinstance(
            provider_response,
            dict,
        ):

            if issubclass(
                output_type,
                BaseModel,
            ):
                return output_type.model_validate(
                    provider_response,
                )

            return provider_response

        raise TypeError(
            f"Unsupported structured output "
            f"{type(provider_response).__name__}"
        )

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
                    parts.append(item)

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

            return "".join(parts)

        return str(content)

    def extract_metadata(
        self,
        message: AIMessage,
    ) -> dict[str, Any]:

        metadata: dict[str, Any] = {}

        for key, value in vars(message).items():

            if key.startswith("_"):
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
                    id=tool.get("id", ""),
                    name=tool.get("name", ""),
                    arguments=tool.get(
                        "args",
                        {},
                    ),
                )
            )

        return tool_calls

    def _parse_text(
        self,
        text: str,
        output_type: type,
    ) -> Any:

        if issubclass(
            output_type,
            BaseModel,
        ):
            return output_type.model_validate_json(
                text,
            )

        return json.loads(
            text,
        )
