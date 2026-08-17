from __future__ import annotations

from .context import RAGContext


class RAGPromptBuilder:
    """
    Builds the knowledge section of the system prompt.
    """

    HEADER = (
        "## Central Knowledge\n\n"

        "Central Knowledge contains accumulated business information and "
        "understanding. It may include business operations, activities, "
        "processes, data, entities, relationships, facts, evidence, findings, "
        "decisions, goals, insights, observations, patterns, assumptions, "
        "and other established business knowledge.\n\n"

        "Central Knowledge is not automatically available in the current "
        "context. When the owner's request requires stored business information, "
        "use the available tool system to retrieve it.\n\n"

        "Use Central Knowledge when the request requires established information "
        "about the business or its current or historical state.\n\n"

        "Do not retrieve Central Knowledge for ordinary conversational requests "
        "when the current conversation already provides enough information.\n\n"

        "Treat retrieved knowledge as supporting information. Distinguish "
        "established information from interpretations or assumptions and do not "
        "invent unsupported information."
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
