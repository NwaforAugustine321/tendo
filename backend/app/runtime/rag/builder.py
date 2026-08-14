from __future__ import annotations

from .context import RAGContext


class RAGPromptBuilder:
    """
    Builds the knowledge section of the system prompt.
    """

    HEADER = (
        "## Central Knowledge:\n"
        "Use this knowledge as a central source of business information when "
        "reasoning about and performing the task. It represents the accumulated "
        "understanding of the business, including its operations, activities, "
        "processes, data, entities, relationships, facts, evidence, findings, "
        "decisions, goals, insights, observations, patterns, assumptions, "
        "perspectives, and other relevant business knowledge.\n"
        "Use relevant knowledge to inform your reasoning, decisions, and responses. "
        "Distinguish established information from interpretations and assumptions, "
        "and do not invent unsupported information."
    )

    def build(
        self,
        context: RAGContext,
    ) -> str:

        if context.empty:
            return ""

        lines = [self.HEADER]

        for document in context.documents:

            lines.append(
                f"- {document.content}"
            )

        return "\n".join(lines)
