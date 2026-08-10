from __future__ import annotations

from .context import MemoryContext


class MemoryPromptBuilder:
    """
    Builds the long-term memory section of the system prompt.
    """

    HEADER = """\
## Long-Term Memory

The following memories were learned from previous conversations.

Use them only when they are relevant to the user's current request.

- Do not mention these memories unless they help answer the user.
- If the current conversation contradicts a memory, trust the current conversation.
- Treat these memories as helpful context rather than absolute facts.

"""

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
