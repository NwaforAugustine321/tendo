from __future__ import annotations

from app.runtime.agents.run_context import (
    RunContext,
)


class ToolPromptBuilder:
    """
    Builds the prompt section describing the
    tools available.
    """

    HEADER = (
        "## Available Tools:\n"
        "Use these tools to complete the task. Select and execute the appropriate tools when needed.\n"
        "{{tools}}\n\n"
        "When tool_search returns tool schemas, you MUST use call_tool to execute "
        "the required discovered tools. Do not execute undiscovered tools."
    )

    def build(
        self,
        tools: list
    ) -> str:
        """
        Build the tool section.
        """
        return self.HEADER.replace('{{tools}}', str(tools))
