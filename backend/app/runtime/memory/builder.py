from __future__ import annotations

from .context import MemoryContext


class MemoryPromptBuilder:
    """
    Builds the long-term memory section of the system prompt.
    """

    HEADER = (
        "## Long-Term Memory:\n"
        "Use this memory as a source of relevant context when performing the task. "
        "It contains accumulated knowledge of the business, including facts, history, "
        "preferences, decisions, insights, patterns, relationships, past history,  and prior observations. "
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
