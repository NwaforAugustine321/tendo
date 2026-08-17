from __future__ import annotations

from .context import MemoryContext


class MemoryPromptBuilder:
    """
    Builds the long-term memory section of the system prompt.
    """

    HEADER = (

        "## Long-Term Memory\n\n"

        "Long-Term Memory contains information remembered from previous "
        "conversations and interactions. It provides persistent context about "
        "the user and their history that may no longer be present in the current "
        "conversation.\n\n"

        "It may contain the user's preferences, communication style, goals, "
        "interests, important personal context, previous decisions, past "
        "requests, ongoing matters, relationships, experiences, facts they "
        "have shared, and other information that is useful for understanding "
        "the user over time.\n\n"

        "Use Long-Term Memory to maintain continuity across conversations and "
        "avoid treating each interaction as if it were the first interaction "
        "with the user. It can provide context from earlier conversations when "
        "that context is relevant to the current request.\n\n"

        "Long-Term Memory is not automatically included in the current context. "
        "When the current conversation does not contain enough context, or when "
        "the request depends on something the user may have previously shared, "
        "remembered, decided, preferred, or discussed, use the available memory "
        "capability to retrieve the relevant information.\n\n"

        "Do not retrieve Long-Term Memory for ordinary conversational turns when "
        "the current conversation already provides sufficient context.\n\n"

        "When retrieving memory, use a focused query describing the specific "
        "context you need. Do not perform broad or unnecessary memory searches.\n\n"

        "Treat retrieved memories as supporting context. Use them when relevant, "
        "but distinguish remembered information from the current conversation "
        "and do not invent information that is not supported by the retrieved "
        "memory."

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
