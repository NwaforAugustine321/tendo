from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.runtime.agents.run_context import RunContext
from app.runtime.chat.context import ChatContext

if TYPE_CHECKING:
    from app.runtime.agents.agent import Agent


@dataclass(slots=True)
class PromptContext:
    """
    Context used when building prompts.
    """

    agent: Agent

    run_context: RunContext

    chat_context: ChatContext
