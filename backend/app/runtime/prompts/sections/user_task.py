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
        "## User Task\n"
        "Complete the user's current request.\n"
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
