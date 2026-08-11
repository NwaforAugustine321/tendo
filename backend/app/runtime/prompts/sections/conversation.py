from __future__ import annotations

from app.runtime.conversation.context import (
    ConversationContext,
)


class ConversationPromptBuilder:
    """
    Builds the conversation history prompt.
    """

    HEADER = (
        "## Conversation History\n"
        "The following conversation occurred before the current user request.\n"
        "Use it only when it provides useful context.\n"
        "Always prioritize the latest user message.\n"
    )

    def build(
        self,
        context: ConversationContext,
    ) -> str:
        """
        Build the conversation history section.
        """

        if context.empty:
            return ""

        lines: list[str] = [
            self.HEADER,
        ]

        #
        # Conversation summary.
        #
        if context.summary:

            lines.extend(
                [
                    "",
                    "### Summary",
                    context.summary.strip(),
                ]
            )

        #
        # Previous messages.
        #
        messages = [
            message
            for message in context.messages
            if message.content
        ]

        if messages:

            lines.extend(
                [
                    "",
                    "### Previous Messages",
                ]
            )

            for message in messages:

                role = getattr(
                    message.role,
                    "value",
                    str(message.role),
                )

                lines.append(
                    f"{role}: {message.content.strip()}"
                )

        return "\n".join(
            lines,
        )
