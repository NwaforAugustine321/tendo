from __future__ import annotations

from .context import RAGContext


class RAGPromptBuilder:
    """
    Builds the knowledge section of the system prompt.
    """

    HEADER = (
        "\n<central_knowledge_instructions>\n"
        "Central Knowledge context contains accumulated business information and "
        "understanding. It may include business operations, activities, "
        "processes, data, entities, relationships, facts, evidence, findings, "
        "decisions, goals, insights, observations, patterns,perspectives, assumptions, "
        "and other established business knowledge.\n\n"
        "Use this knowledge as a central source of business information when "
        "reasoning about and performing the task\n\n"
        "Use relevant knowledge to inform your reasoning, decisions, and responses. "
        "Distinguish established information from interpretations and assumptions, "
        "and do not invent unsupported information.\n\n"
        "<central_knowledge>\n"
        "{central_knowledge}\n"
        "<\central_knowledge>\n"
        "<central_knowledge_instructions>\n"
    )

    def build(
        self,
        context: RAGContext,
    ) -> str:

        if context.empty:
            return ""

        lines = []

        for document in context.documents:

            lines.append(
                f"- {document.content}"
            )

        lines = '\n'.join(lines)
        return self.HEADER.replace('{central_knowledge}', lines)
