from __future__ import annotations

from app.runtime.agents.run_context import (
    RunContext,
)


class UserTaskPromptBuilder:
    """
    Builds the prompt section describing the
    current user request.
    """

    HEADER = (
        "## User Task:\n"
        "Complete the current task using the relevant information available in "
        "Central Knowledge, Long-Term Memory, and Conversation History. "
        "Use these sources together to understand the business, maintain continuity, "
        "apply remembered preferences and context, and make informed decisions. "
        "Prioritize the current task while grounding your reasoning in relevant context."
    )

    def build(
        self,
        context: RunContext,
    ) -> str:
        """
        Build the user task section.
        """

        user_request = context.user_request.strip()

        if not user_request:
            return ""

        return "\n".join(
            [
                self.HEADER,
                user_request,
            ]
        )
