from __future__ import annotations
from collections.abc import Callable
from typing import Any, Literal
from pydantic import BaseModel, Field
from app.lib.i18n import _get_i18n
from app.lib.tool_schema import tools_schema_and_description

def _slice(key: str) -> str:
    """Get a raw prompt slice template from translations."""
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")


class StandardPromptResult(BaseModel):

    prompt: str = Field(default="")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) and getattr(self, key) is not None


class SystemPromptResult(StandardPromptResult):

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

    tools: list[Any] = []

    agent: Any = Field(description="Reference to the agent using these prompts")

    def task_execution(self) -> SystemPromptResult | StandardPromptResult:

        slices: list[COMPONENTS] = ["role_playing"]

        if len(self.tools) > 0:
            slices.append("tools")
        else:
            slices.append("no_tools")

        return self._build_prompt(slices)

    def _build_prompt(
        self,
        components: list[COMPONENTS],
    ) -> str:

        prompt:str = ''.join([
            f"{_slice(component)}\n\n" for component in components
        ])

        return prompt.replace("{goal}", self.agent.goal).replace("{role}", self.agent.role).replace("{backstory}", self.agent.backstory).replace("{tools}", tools_schema_and_description(self.tools))
        


def build_execution_prompt(
    agent: Any,
    tools: list[Any],
) -> tuple[SystemPromptResult | StandardPromptResult, list[str], Callable[[], bool] | None]:

    prompt = Prompts(
        agent=agent,
        tools=tools,
    ).task_execution()

    stop_words = [_slice("observation")]

    return prompt, stop_words
