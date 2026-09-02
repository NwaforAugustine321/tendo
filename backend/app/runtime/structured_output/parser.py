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

            (
                action,
                content,
                question,
                interaction,
            ) = self.extract_protocol(
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
                interaction=interaction,
                question=question,
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
            "<question>...</question>\n\n"
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

        if content:
            return content.strip()

        if action is None:
            return self.extract_text_outside_tags(
                raw_text,
            )

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
        *,
        interaction: str | None = None,
        question: str | None = None,
    ) -> tuple[LLMAction | None, str | None]:

        if not value:
            return (
                None,
                None,
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

    def extract_protocol(
        self,
        text: str,
    ) -> tuple[
        str | None,
        str | None,
        str | None,
        str | None,
    ]:
        """
        Resolve the protocol from the complete LLM response.

        Priority:
        1. request_user_input with a non-empty question.
        2. continue with content.
        3. final with content.
        4. Any valid continue/final action.
        5. No action, but preserve meaningful content.
        """

        blocks = self.extract_action_blocks(text)

        request_block = None
        continue_block = None
        final_block = None

        for block in blocks:
            action = block["action"]

            if action == LLMAction.REQUEST_USER_INPUT.value:
                question = block["question"]

                if question:
                    request_block = block
                    break

            elif action == LLMAction.CONTINUE.value:
                if continue_block is None:
                    continue_block = block

            elif action == LLMAction.FINAL.value:
                if final_block is None:
                    final_block = block

        if request_block is not None:
            return (
                request_block["action"],
                request_block["content"],
                request_block["question"],
                request_block["interaction"],
            )

        if continue_block is not None and continue_block["content"]:
            return (
                continue_block["action"],
                continue_block["content"],
                None,
                None,
            )

        if final_block is not None and final_block["content"]:
            return (
                final_block["action"],
                final_block["content"],
                None,
                None,
            )

        # A valid action without content is not enough to expose the
        # action as the response. Fall back to meaningful untagged or
        # standalone content, which may already be the final answer.
        content = self.extract_content(text)

        if content:
            return (
                None,
                content,
                None,
                None,
            )

        return (
            None,
            self.extract_text_outside_tags(text),
            None,
            None,
        )

    def extract_action_blocks(
        self,
        text: str,
    ) -> list[dict[str, str | None]]:
        """
        Extract complete action protocol blocks instead of pairing
        unrelated tags from different parts of the response.
        """

        pattern = re.compile(
            r"<action\b[^>]*>\s*"
            r"(.*?)"
            r"\s*</action>",
            re.IGNORECASE | re.DOTALL,
        )

        blocks: list[dict[str, str | None]] = []
        matches = list(pattern.finditer(text))

        for index, match in enumerate(matches):
            action = match.group(1).strip().lower()

            block_end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )
            block_text = text[match.end():block_end]

            content_match = re.search(
                r"<content\b[^>]*>\s*(.*?)\s*</content>",
                block_text,
                re.IGNORECASE | re.DOTALL,
            )

            question_match = re.search(
                r"<question\b[^>]*>\s*(.*?)\s*</question>",
                block_text,
                re.IGNORECASE | re.DOTALL,
            )

            interaction_match = re.search(
                r"<interaction\b[^>]*>\s*(.*?)\s*</interaction>",
                block_text,
                re.IGNORECASE | re.DOTALL,
            )

            blocks.append(
                {
                    "action": action or None,
                    "content": (
                        content_match.group(1).strip()
                        if content_match
                        else None
                    ),
                    "question": (
                        question_match.group(1).strip()
                        if question_match
                        else None
                    ),
                    "interaction": (
                        interaction_match.group(1).strip()
                        if interaction_match
                        else None
                    ),
                },
            )

        return blocks

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
        # request_user_input requires only:
        #
        # <action>request_user_input</action>
        # <content>...</content>
        # <question>...</question>
        #
        # <interaction> is NOT part of the LLM XML protocol.
        # The internal Interaction object is created here for runtime
        # compatibility.
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

            return (
                Interaction(
                    type=InteractionType.USER_INPUT,
                ),
                None,
            )

        # ---------------------------------------------------------
        # No action is valid when the parser has fallen back to
        # meaningful response content.
        # ---------------------------------------------------------

        if action is None:
            return (
                None,
                None,
            )

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

            protocol_action, _, protocol_question, _ = (
                self.extract_protocol(
                    self.extract_text(
                        provider_response,
                    ),
                )
            )

            if protocol_action or protocol_question:

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
