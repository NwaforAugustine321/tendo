"""Prompt generation and management utilities for agents."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.lib.i18n import _get_i18n


def _slice(key: str) -> str:
    """Get a raw prompt slice template from translations."""
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")


class StandardPromptResult(BaseModel):
    """Result with only prompt field for standard mode."""

    prompt: str = Field(default="")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) and getattr(self, key) is not None


class SystemPromptResult(StandardPromptResult):
    """Result with system, user, and prompt fields for system prompt mode."""

    system: str = Field(default="")
    user: str = Field(default="")


COMPONENTS = Literal[
    "role_playing",
    "tools",
    "no_tools",
    "native_tools",
    "task",
    "native_task",
    "task_no_tools",
]


class Prompts(BaseModel):
    """Manages and generates prompts for a generic agent.

    Notes:
        - Need to refactor so that prompt is not tightly coupled to agent.
    """

    has_tools: bool = Field(
        default=False, description="Indicates if the agent has access to tools"
    )
    use_native_tool_calling: bool = Field(
        default=False,
        description="Whether to use native function calling instead of ReAct format",
    )
    system_template: str | None = Field(
        default=None, description="Custom system prompt template"
    )
    prompt_template: str | None = Field(
        default=None, description="Custom user prompt template"
    )
    response_template: str | None = Field(
        default=None, description="Custom response prompt template"
    )
    use_system_prompt: bool = Field(
        default=False,
        description="Whether to use the system prompt when no custom templates are provided",
    )
    agent: Any = Field(description="Reference to the agent using these prompts")

    def task_execution(self) -> SystemPromptResult | StandardPromptResult:
        """Generate a standard prompt for task execution.

        Returns:
            A dictionary containing the constructed prompt(s).
        """
        slices: list[COMPONENTS] = ["role_playing"]

        if self.has_tools:
            if not self.use_native_tool_calling:
                slices.append("tools")
        else:
            slices.append("no_tools")

        system: str = self._build_prompt(slices)

        task_slice: COMPONENTS
        if self.use_native_tool_calling:
            task_slice = "native_task"
        elif self.has_tools:
            task_slice = "task"
        else:
            task_slice = "task_no_tools"

        slices.append(task_slice)

        if (
            not self.system_template
            and not self.prompt_template
            and self.use_system_prompt
        ):
            return SystemPromptResult(
                system=system,
                user=self._build_prompt([task_slice]),
                prompt=self._build_prompt(slices),
            )

        return StandardPromptResult(
            prompt=self._build_prompt(
                slices,
                self.system_template,
                self.prompt_template,
                self.response_template,
            )
        )

    def _build_prompt(
        self,
        components: list[COMPONENTS],
        system_template: str | None = None,
        prompt_template: str | None = None,
        response_template: str | None = None,
    ) -> str:
        """Constructs a prompt string from specified components.

        Args:
            components: List of component names to include in the prompt.
            system_template: Optional custom template for the system prompt.
            prompt_template: Optional custom template for the user prompt.
            response_template: Optional custom template for the response prompt.

        Returns:
            The constructed prompt string.
        """
        prompt: str

        if not system_template or not prompt_template:
            prompt_parts: list[str] = [_slice(component) for component in components]
            prompt = "".join(prompt_parts)
        else:
            template_parts: list[str] = [
                _slice(component)
                for component in components
                if component != "task"
            ]
            system: str = system_template.replace(
                "{{ .System }}", "".join(template_parts)
            )
            prompt = prompt_template.replace(
                "{{ .Prompt }}", "".join(_slice("task"))
            )
            if response_template:
                response: str = response_template.split("{{ .Response }}")[0]
                prompt = f"{system}\n{prompt}\n{response}"
            else:
                prompt = f"{system}\n{prompt}"

        return (
            prompt.replace("{goal}", self.agent.goal)
            .replace("{role}", self.agent.role)
            .replace("{backstory}", self.agent.backstory)
        )


def build_execution_prompt(
    agent: Any,
    tools: list[Any],
    use_system_prompt: bool = False,
    system_template: str | None = None,
    prompt_template: str | None = None,
    response_template: str | None = None,
) -> tuple[SystemPromptResult | StandardPromptResult, list[str], Callable[[], bool] | None]:
    """Build the execution prompt, stop words, and RPM limit function.

    Args:
        agent: The agent instance (must have .goal, .role, .backstory attributes).
        tools: The tools available to the agent.
        use_system_prompt: Whether to use system prompt mode.
        system_template: Custom system prompt template.
        prompt_template: Custom user prompt template.
        response_template: Custom response prompt template.

    Returns:
        A tuple of (prompt, stop_words, rpm_limit_fn).
    """
    use_native_tool_calling = getattr(agent, "use_native_tool_calling", False)

    prompt = Prompts(
        agent=agent,
        has_tools=len(tools) > 0,
        use_native_tool_calling=use_native_tool_calling,
        use_system_prompt=use_system_prompt,
        system_template=system_template,
        prompt_template=prompt_template,
        response_template=response_template,
    ).task_execution()

    stop_words = [_slice("observation")]

    if response_template:
        stop_words.append(
            response_template.split("{{ .Response }}")[1].strip()
        )

    rpm_controller = getattr(agent, "_rpm_controller", None)
    rpm_limit_fn: Callable[[], bool] | None = (
        rpm_controller.check_or_wait if rpm_controller else None
    )

    return prompt, stop_words, rpm_limit_fn
