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
        "\nUSER_TASK_TO_PROCESS:\n"
        "{task}"

    )

    def build(
        self,
        message: str,
    ) -> str:

        if not message:
            return ""

        return self.HEADER.replace("{task}", str(message))
