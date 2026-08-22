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
        "when necessary to preserve continuity and consistency.\n"
        "Conversation Summary Context:\n"
        "{summary}\n\n"
        "Previous Messages Context:\n"
        "{previous_messages}\n\n"
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

        lines: list[str] = []

        #
        # Conversation summary.
        #
        if context.summary:
            self.HEADER = self.HEADER.replace(
                "{summary}", context.summary.strip())

        #
        # Previous messages.
        #
        messages = [
            message
            for message in context.messages
            if message.content
        ]

        if messages:

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
                    f"<{role if role != 'system' else ''}>: {content.strip()}"
                )

        lines = "\n".join(lines)
        return self.HEADER.replace('{previous_messages}', lines)
