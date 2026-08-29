from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolUseCall:
    """
    Tracks tool usage during a single agent run.

    ToolUseCall is responsible for tracking and describing tool usage.
    It does not decide whether a tool result is useful. The runner/LLM
    execution flow determines usefulness and records it through
    record_result().
    """

    max_tool_search_calls: int = 4
    max_same_search_query: int = 2

    search_calls: int = 0

    search_queries: list[str] = field(default_factory=list)

    discovered_tools: set[str] = field(default_factory=set)

    executed_calls: set[tuple[str, str]] = field(default_factory=set)

    tool_call_counts: dict[str, int] = field(default_factory=dict)

    successful_tools: set[str] = field(default_factory=set)

    failed_tools: set[str] = field(default_factory=set)

    last_tool: str | None = None
    last_tool_result: Any = None

    def record_search(self, query: str) -> None:
        query = query.strip()
        self.search_calls += 1
        self.search_queries.append(query)

    def can_search(self, query: str) -> bool:
        query = query.strip()

        if self.search_calls >= self.max_tool_search_calls:
            return False

        return self.search_count(query) < self.max_same_search_query

    def search_count(self, query: str) -> int:
        query = query.strip()
        return sum(item == query for item in self.search_queries)

    def record_discovered_tools(self, tools: list[str]) -> None:
        self.discovered_tools.update(tools)

    def has_discovered(self, tool_name: str) -> bool:
        return tool_name in self.discovered_tools

    @staticmethod
    def normalize_arguments(arguments: dict[str, Any]) -> str:
        return json.dumps(
            arguments,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )

    def execution_key(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> tuple[str, str]:
        return (
            tool_name,
            self.normalize_arguments(arguments),
        )

    def has_executed(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> bool:
        return (
            self.execution_key(tool_name, arguments)
            in self.executed_calls
        )

    def record_execution(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> None:
        key = self.execution_key(tool_name, arguments)

        self.executed_calls.add(key)

        self.tool_call_counts[tool_name] = (
            self.tool_call_counts.get(tool_name, 0) + 1
        )

        self.last_tool = tool_name

    def record_result(
        self,
        tool_name: str,
        output: Any,
        *,
        useful: bool,
    ) -> None:
        """
        Record the runner/LLM's evaluation of a tool result.

        ToolUseCall does not determine usefulness itself.
        """
        self.last_tool = tool_name
        self.last_tool_result = output

        if useful:
            self.successful_tools.add(tool_name)
            self.failed_tools.discard(tool_name)
        else:
            self.failed_tools.add(tool_name)

    def tool_count(self, tool_name: str) -> int:
        return self.tool_call_counts.get(tool_name, 0)

    def was_successful(self, tool_name: str) -> bool:
        return tool_name in self.successful_tools

    def was_failed(self, tool_name: str) -> bool:
        return tool_name in self.failed_tools

    def has_executed_any_tool(self) -> bool:
        return bool(self.executed_calls)

    def has_multiple_tools(self) -> bool:
        return len(
            {tool_name for tool_name, _ in self.executed_calls}
        ) > 1

    def available_untried_tools(self) -> list[str]:
        return [
            tool_name
            for tool_name in self.discovered_tools
            if tool_name not in self.successful_tools
            and tool_name not in self.failed_tools
        ]

    def should_try_another_tool(self) -> bool:
        return bool(
            self.discovered_tools - self.successful_tools
        )

    def reset_last_result(self) -> None:
        self.last_tool = None
        self.last_tool_result = None

    def tracking_tool_name(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """
        Resolve the underlying tool name when the exposed tool is
        a generic dispatcher such as call_tool.
        """
        if tool_name != "call_tool":
            return tool_name

        for key in ("tool_name", "name", "tool"):
            value = arguments.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return tool_name

    def tracking_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve the arguments that identify the underlying tool call.

        For call_tool, dispatcher wrapper fields are removed when
        possible so duplicate detection compares the actual target
        tool and its arguments.
        """
        if tool_name != "call_tool":
            return dict(arguments)

        for key in ("arguments", "params", "parameters", "args"):
            nested = arguments.get(key)

            if isinstance(nested, dict):
                return dict(nested)

        return {
            key: value
            for key, value in arguments.items()
            if key not in {"tool_name", "name", "tool"}
        }

    def extract_search_query(
        self,
        arguments: dict[str, Any],
    ) -> str:
        query = arguments.get("query", "")

        if query is None:
            return ""

        return str(query).strip()

    def extract_discovered_tools(
        self,
        output: Any,
    ) -> list[str]:
        """
        Extract tool names from common discovery-result formats.

        This is intentionally generic and contains no Memory/RAG-specific
        behavior.
        """
        if output is None:
            return []

        if isinstance(output, dict):
            for key in (
                "tools",
                "discovered_tools",
                "available_tools",
            ):
                value = output.get(key)

                if isinstance(value, list):
                    return [
                        str(item)
                        for item in value
                        if item
                    ]

        text = getattr(output, "observation", output)

        if not isinstance(text, str):
            return []

        return re.findall(
            r"^\s*\d+\.\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.MULTILINE,
        )

    def runtime_step_guidance(
        self,
        *,
        remaining_steps: int,
        max_iterations: int,
    ) -> str | None:
        if remaining_steps > (max_iterations * 0.5):
            return None

        if remaining_steps <= 1:
            return (
                f"You have {remaining_steps} interaction step remaining.\n"
                "Complete the task now. If no further tool action is "
                "essential, provide the final user-facing response."
            )

        if remaining_steps <= (max_iterations * 0.3):
            return (
                f"You have {remaining_steps} interaction steps remaining.\n"
                "Prioritize the most important remaining action and "
                "prepare to finish the task."
            )

        return (
            f"You have {remaining_steps} interaction steps remaining.\n"
            "Use them efficiently to complete the task."
        )

    def build_tool_usage_guidance(self) -> str:
        """
        Build runtime guidance for the next LLM iteration.
        """
        lines = [
            "TOOL EXECUTION GUIDANCE:",
            "",
            "1. Do not repeat the exact same tool call with the same arguments.",
            "2. If a tool result is insufficient, change the query or use another available tool.",
            "3. If another discovered tool can provide the missing information, use it.",
            "4. Once tool_search has discovered tools, prefer call_tool to execute the discovered capability.",
            "5. If the previous tool did not provide useful information, try another discovered tool before asking the user to repeat information.",
            "6. Use tool results to determine whether the task can now be completed.",
            "7. If the available tool results are sufficient, stop using tools and provide the final answer.",
            "8. If more information is required, perform the next necessary tool action rather than asking the user for information that may already be obtainable through tools.",
            "",
            f"Tool searches performed: {self.search_calls}",
            f"Discovered tools: {', '.join(sorted(self.discovered_tools)) or 'none'}",
            f"Executed tools: {', '.join(sorted(self.tool_call_counts)) or 'none'}",
        ]

        if self.last_tool:
            lines.extend([
                "",
                f"Last tool used: {self.last_tool}",
                "Last tool status: result available for evaluation.",
            ])

        if self.failed_tools:
            lines.extend([
                "",
                "Tools that did not provide sufficient information:",
                ", ".join(sorted(self.failed_tools)),
                "Prefer a changed query or another discovered tool instead of repeating the same call.",
            ])

        if self.successful_tools:
            lines.extend([
                "",
                "Tools that have already produced sufficient information:",
                ", ".join(sorted(self.successful_tools)),
            ])

        if self.discovered_tools:
            lines.extend([
                "",
                "DISCOVERY COMPLETE.",
                "Use call_tool to execute one of the discovered tools.",
                "Do not call tool_search again unless the discovered tools genuinely cannot provide the required capability.",
            ])

        return "\n".join(lines)

    def summary(self) -> dict[str, Any]:
        return {
            "search_calls": self.search_calls,
            "search_queries": list(self.search_queries),
            "discovered_tools": sorted(self.discovered_tools),
            "executed_calls": len(self.executed_calls),
            "tool_call_counts": dict(self.tool_call_counts),
            "successful_tools": sorted(self.successful_tools),
            "failed_tools": sorted(self.failed_tools),
            "last_tool": self.last_tool,
        }
