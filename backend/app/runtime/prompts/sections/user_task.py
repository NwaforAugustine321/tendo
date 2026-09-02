from __future__ import annotations

from app.runtime.agents.run_context import (
    RunContext,
)

import re


class UserTaskPromptBuilder:
    """
    Builds the prompt section describing the
    current user request.
    """

    HEADER = (
        "[CURRENT TASK]\n"
        "{task}\n"
        "[CURRENT TASK]"
    )

    def build(
        self,
        message: str,
    ) -> str:

        if not message:
            return ""

        return self.HEADER.replace("{task}",  message)
