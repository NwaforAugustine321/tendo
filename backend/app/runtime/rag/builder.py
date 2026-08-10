from __future__ import annotations

from collections import defaultdict

from .context import RAGContext


class RAGPromptBuilder:
    """
    Builds the knowledge section of the system prompt.
    """

    HEADER = """\
## Knowledge

The following documents were retrieved because they may
help answer the user's request.

Use them only when they are relevant.

- Do not mention these documents unless they help answer
  the user.
- If the retrieved knowledge conflicts with the current
  conversation, trust the current conversation.
"""

    def build(
        self,
        context: RAGContext,
    ) -> str:

        if context.empty:
            return ""

        groups: dict[str, list] = defaultdict(list)

        for document in context.documents:

            source = (
                document.source.strip()
                or "General"
            )

            groups[source].append(
                document,
            )

        lines = [self.HEADER]

        for source, documents in groups.items():

            lines.append("")
            lines.append(
                f"### {source}"
            )

            for document in documents:

                lines.append(
                    f"- {document.content}"
                )

        return "\n".join(lines)
