from __future__ import annotations

from .context import MemoryContext


class MemoryPromptBuilder:
    """
    Builds the long-term memory section of the system prompt.
    """

    HEADER = (
        "## Long-Term Memory\n\n"
        "Long-Term Memory contains information remembered from previous"
        "conversations and interactions. It provides context about "
        "the user and their history that may no longer be present any more in the context\n\n"
        "It may contain the user's preferences, communication style, goals, "
        "interests, important personal context, previous decisions, past "
        "requests, ongoing matters, relationships, experiences, facts they "
        "have shared, and other information that is useful for understanding "
        "the user over time.\n\n"
        "Use relevant memory to inform your reasoning and response. "
        "Do not ignore relevant memory, but do not invent or assume information "
        "that is not supported by the memory."

    )

    def build(
        self,
        context: MemoryContext,
    ) -> str:
        """
        Convert retrieved memories into a prompt section.
        """

        if context.empty:
            return ""

        lines = [self.HEADER]

        for entry in context.entries:

            lines.append(
                f"- {entry.text}"
            )

        return "\n".join(lines)
