from __future__ import annotations

from app.runtime.conversation.context import (
    ConversationContext,
)


class ConversationPromptBuilder:
    """
    Builds the conversation history prompt.
    """
    HEADER = (
        "## Conversation History:\n"
        "Use this conversation history to maintain continuity and understand the "
        "ongoing business context. It contains previous interactions, discussions, "
        "requests, decisions, questions, answers, preferences, clarifications, "
        "commitments, tasks, and other context established during the conversation.\n"
        "Use relevant history when reasoning, responding, or continuing ongoing work. "
        "Prioritize recent and relevant information while using earlier interactions "
        "when necessary to preserve continuity and consistency."
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
