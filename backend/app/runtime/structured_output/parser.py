from __future__ import annotations

import json
import re

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
            return self.parser_error_response(
                provider_response=provider_response,
                raw_text=str(provider_response),
                error=(
                    "Unsupported provider response type "
                    f"'{type(provider_response).__name__}'. "
                    "The response could not be processed."
                ),
            )

        print(
            "raw text from llm>>>",
            provider_response,
        )

        try:

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

            # -----------------------------------------------------
            # Parse action.
            # -----------------------------------------------------

            parsed_action, action_error = self.parse_action(
                action,
            )

            if action_error:

                return self.parser_error_response(
                    provider_response=provider_response,
                    raw_text=raw_text,
                    error=action_error,
                )

            # -----------------------------------------------------
            # Validate interaction protocol.
            # -----------------------------------------------------

            (
                parsed_interaction,
                interaction_error,
            ) = self.parse_interaction(
                action=parsed_action,
                interaction=interaction,
                question=question,
            )

            if interaction_error:

                return self.parser_error_response(
                    provider_response=provider_response,
                    raw_text=raw_text,
                    error=interaction_error,
                )

            # -----------------------------------------------------
            # Parse structured output.
            # -----------------------------------------------------

            output, output_error = self.parse_output(
                provider_response=provider_response,
                output_type=output_type,
            )

            if output_error:

                return self.parser_error_response(
                    provider_response=provider_response,
                    raw_text=raw_text,
                    error=output_error,
                )

            # -----------------------------------------------------
            # Resolve response text.
            # -----------------------------------------------------

            user_text = self.resolve_text(
                raw_text=raw_text,
                content=content,
                action=parsed_action,
            )

            return LLMResponse(
                text=user_text,
                content=user_text,
                question=question,
                output=output,
                tool_calls=tool_calls,
                metadata=self.extract_metadata(
                    provider_response,
                ),
                raw=provider_response,
                action=parsed_action,
                interaction=parsed_interaction,
            )

        except Exception as error:

            return self.parser_error_response(
                provider_response=provider_response,
                raw_text=self.safe_extract_text(
                    provider_response,
                ),
                error=(
                    "The response could not be parsed "
                    "successfully. "
                    f"Parser error: {type(error).__name__}: {error}"
                ),
            )

    def parser_error_response(
        self,
        *,
        provider_response: Any,
        raw_text: str,
        error: str,
    ) -> LLMResponse:

        correction_message = self.build_parser_error_message(
            error=error,
        )

        if isinstance(
            provider_response,
            AIMessage,
        ):
            metadata = self.extract_metadata(
                provider_response,
            )
        else:
            metadata = {}

        metadata["parser_error"] = True
        metadata["parser_error_message"] = error
        metadata["parser_raw_output"] = raw_text

        return LLMResponse(
            text=correction_message,
            content=correction_message,
            question=None,
            output=None,
            tool_calls=[],
            metadata=metadata,
            raw=provider_response,
            action=None,
            interaction=None,
        )

    def build_parser_error_message(
        self,
        *,
        error: str,
    ) -> str:

        return (
            "LLM RESPONSE PROTOCOL ERROR.\n\n"
            f"{error}\n\n"
            "Correct the response and produce a new response "
            "using ONLY the required XML tags.\n\n"
            "VALID ACTIONS:\n"
            "<action>continue</action>\n"
            "<action>final</action>\n"
            "<action>request_user_input</action>\n\n"
            "FOR continue:\n"
            "<action>continue</action>"
            "<content>Briefly describe the concrete internal step.</content>\n\n"
            "FOR final:\n"
            "<action>final</action>"
            "<content>Complete answer for the user.</content>\n\n"
            "FOR request_user_input:\n"
            "<action>request_user_input</action>"
            "<content>Briefly explain why user input is required.</content>"
            "<question>One clear question for the user.</question>"
            "<interaction>user_input</interaction>\n\n"
            "Do not output JSON, markdown, explanations, or text "
            "outside the required tags."
        )

    # =============================================================
    # Text resolution
    # =============================================================

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

        pattern = re.compile(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            re.IGNORECASE | re.DOTALL,
        )

        return pattern.sub(
            "",
            text,
        )

    # =============================================================
    # Action parsing
    # =============================================================

    def parse_action(
        self,
        value: str | None,
    ) -> tuple[LLMAction | None, str | None]:

        if not value:

            return (
                None,
                (
                    "The <action> tag is missing. "
                    "A response must contain exactly one valid action: "
                    "continue, final, or request_user_input."
                ),
            )

        normalized = value.strip().lower()

        try:

            return (
                LLMAction(
                    normalized,
                ),
                None,
            )

        except Exception:

            return (
                None,
                (
                    f"Unsupported action '{value}'. "
                    "The <action> tag must contain exactly one of: "
                    "continue, final, request_user_input."
                ),
            )

    # =============================================================
    # Interaction parsing
    # =============================================================

    def parse_interaction(
        self,
        *,
        action: LLMAction | None,
        interaction: str | None,
        question: str | None,
    ) -> tuple[Interaction | None, str | None]:

        # ---------------------------------------------------------
        # No interaction is allowed for normal processing.
        # ---------------------------------------------------------

        if action in {
            LLMAction.CONTINUE,
            LLMAction.FINAL,
        }:

            if interaction:

                return (
                    None,
                    (
                        f"The <interaction>{interaction}"
                        "</interaction> tag is not allowed for "
                        f"the '{action.value}' action. "
                        "Only request_user_input may contain an "
                        "interaction tag."
                    ),
                )

            if question:

                return (
                    None,
                    (
                        f"The <question> tag is not allowed for "
                        f"the '{action.value}' action. "
                        "Only request_user_input may contain "
                        "a question."
                    ),
                )

            return (
                None,
                None,
            )

        # ---------------------------------------------------------
        # request_user_input requires:
        #
        # <question>...</question>
        # <interaction>user_input</interaction>
        # ---------------------------------------------------------

        if action == LLMAction.REQUEST_USER_INPUT:

            if not question:

                return (
                    None,
                    (
                        "The request_user_input action requires "
                        "a non-empty <question> tag."
                    ),
                )

            if not interaction:

                return (
                    None,
                    (
                        "The request_user_input action requires "
                        "<interaction>user_input</interaction>."
                    ),
                )

            normalized = interaction.strip().lower()

            if (
                normalized
                != InteractionType.USER_INPUT.value
            ):

                return (
                    None,
                    (
                        f"Unsupported interaction type "
                        f"'{interaction}'. "
                        "The only supported interaction type is "
                        "'user_input'."
                    ),
                )

            return (
                Interaction(
                    type=InteractionType.USER_INPUT,
                ),
                None,
            )

        # ---------------------------------------------------------
        # Missing/invalid action should normally already have been
        # caught by parse_action, but keep this defensive path.
        # ---------------------------------------------------------

        return (
            None,
            (
                "The response does not contain a valid action. "
                "Use continue, final, or request_user_input."
            ),
        )

    # =============================================================
    # Structured output
    # =============================================================

    def parse_output(
        self,
        *,
        provider_response: Any,
        output_type: type | None,
    ) -> tuple[Any, str | None]:

        if output_type is None:

            return (
                None,
                None,
            )

        try:

            if isinstance(
                provider_response,
                output_type,
            ):

                return (
                    provider_response,
                    None,
                )

        except Exception as error:

            return (
                None,
                (
                    "The requested output type could not be "
                    "validated. "
                    f"{type(error).__name__}: {error}"
                ),
            )

        if isinstance(
            provider_response,
            AIMessage,
        ):

            if self.extract_action(
                self.extract_text(
                    provider_response,
                ),
            ):

                return (
                    None,
                    None,
                )

            output, error = self._parse_text(
                text=self.extract_text(
                    provider_response,
                ),
                output_type=output_type,
            )

            return (
                output,
                error,
            )

        if isinstance(
            provider_response,
            dict,
        ):

            try:

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

                    return (
                        output_type.model_validate(
                            provider_response,
                        ),
                        None,
                    )

                return (
                    provider_response,
                    None,
                )

            except Exception as error:

                return (
                    None,
                    (
                        "The structured output could not be "
                        "validated. "
                        f"{type(error).__name__}: {error}"
                    ),
                )

        return (
            None,
            (
                "Unsupported structured output "
                f"'{type(provider_response).__name__}'. "
                "Must return the expected structured "
                "output format."
            ),
        )

    # =============================================================
    # Tag extraction
    # =============================================================

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

    # =============================================================
    # Provider response extraction
    # =============================================================

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
                        str(item),
                    )

            return "".join(
                parts,
            )

        return str(
            content,
        )

    def safe_extract_text(
        self,
        provider_response: Any,
    ) -> str:

        try:

            if isinstance(
                provider_response,
                AIMessage,
            ):

                return self.extract_text(
                    provider_response,
                )

            return str(
                provider_response,
            )

        except Exception:

            return "<unable to extract provider response>"

    def extract_metadata(
        self,
        message: AIMessage,
    ) -> dict[str, Any]:

        metadata: dict[str, Any] = {}

        try:

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

        except Exception as error:

            metadata["metadata_extraction_error"] = (
                f"{type(error).__name__}: {error}"
            )

        return metadata

    def extract_tool_calls(
        self,
        message: AIMessage,
    ) -> list[ToolCall]:

        tool_calls: list[ToolCall] = []

        try:

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

        except Exception:

            return []

        return tool_calls

    # =============================================================
    # JSON / Pydantic parsing
    # =============================================================

    def _parse_text(
        self,
        *,
        text: str,
        output_type: type,
    ) -> tuple[Any, str | None]:

        text = text.strip()

        if not text:

            return (
                None,
                (
                    "The  returned empty structured output. "
                    "Return the required structured response."
                ),
            )

        try:

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

                return (
                    output_type.model_validate_json(
                        text,
                    ),
                    None,
                )

        except Exception as error:

            return (
                None,
                (
                    "The returned structured output that "
                    "could not be validated. "
                    f"{type(error).__name__}: {error}"
                ),
            )

        try:

            return (
                json.loads(
                    text,
                ),
                None,
            )

        except Exception as error:

            return (
                None,
                (
                    "Invalid JSON structured "
                    "output. "
                    f"{type(error).__name__}: {error}"
                ),
            )
