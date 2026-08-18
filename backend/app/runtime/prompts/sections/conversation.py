from __future__ import annotations

from app.runtime.conversation.context import (
    ConversationContext,
)


class ConversationPromptBuilder:
    """
    Builds the conversation history prompt.
    """
    HEADER = (
        "\nConversation History:\n"
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
                    "\nConversation Summary",
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
                    "\nPrevious Messages",
                ]
            )

            for message in messages:

                role = getattr(
                    message.role,
                    "value",
                    str(message.role),
                )

                content = message.content
                if isinstance(content, (list, tuple)):
                    content = "".join(str(s) for s in content)
                else:
                    content = str(content)

                lines.append(
                    f"{role if role != 'system' else ''}: {content.strip()}"
                )

        return "\n".join(
            lines,
        )
