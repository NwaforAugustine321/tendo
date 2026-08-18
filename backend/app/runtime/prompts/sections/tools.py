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

        "\nTool System:\n"

        "Tools provide capabilities and access to information that may not "
        "already exist in the current conversation.\n\n"

        "When additional information or an action is required, first determine "
        "whether an appropriate capability is available through tool discovery.\n\n"

        "Tool discovery and tool execution are separate operations.\n\n"

        "### tool_search\n\n"

        "`tool_search` discovers available capabilities. Its result describes "
        "the tools that are available; it does not execute those tools and "
        "does not provide the requested information itself.\n\n"

        "When you need a capability that is not already available in the current "
        "context, use `tool_search` with a concise query describing the "
        "information or capability required.\n\n"

        "Do not treat a tool-search result as the answer to the owner's request.\n\n"

        "### call_tool\n\n"

        "`call_tool` executes a tool that was previously discovered by "
        "`tool_search`.\n\n"

        "After discovering a tool, use `call_tool` with the exact discovered "
        "tool name and its required parameters to obtain the actual result.\n\n"

        "Never use `call_tool` to execute `tool_search`.\n\n"

        "Never pass `tool_search` or `call_tool` as the target tool name of "
        "`call_tool`.\n\n"

        "When executing a discovered tool, use the exact tool name returned by "
        "tool discovery and provide a focused query or the required parameters.\n\n"

        "### Tool results\n\n"

        "Use the actual tool result to determine whether the owner's request "
        "can be completed.\n\n"

        "If a tool result is insufficient, change the query or use another "
        "appropriate discovered capability.\n\n"

        "Do not repeatedly execute the same tool with the same arguments.\n\n"

        "Do not continue tool discovery when an appropriate discovered "
        "capability is already available."

        "## Available Tools:\n\n"

        "{{tools}}\n\n"
    )

    def build(
        self,
        tools: list
    ) -> str:
        """
        Build the tool section.
        """
        return self.HEADER.replace('{{tools}}', str(tools))
