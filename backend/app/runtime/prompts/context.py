from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.runtime.agents.run_context import (
    RunContext,
)
from app.runtime.chat.message import (
    ChatMessage,
)
from app.runtime.conversation.context import (
    ConversationContext,
)

if TYPE_CHECKING:
    from app.runtime.agents.agent import Agent


@dataclass(slots=True)
class PromptState:
    """
    Runtime state for prompt construction.

    Stable prompt components are prepared once and reused
    across inference calls for the current session.

    Dynamic content such as:

    - conversation history
    - current user task
    - memory
    - RAG results
    - current execution messages

    is not stored here.
    """

    stable_messages: list[ChatMessage] = field(
        default_factory=list,
    )

    prepared: bool = False


@dataclass(slots=True)
class PromptContext:
    """
    Context used when building prompts.

    PromptState is supplied by the AgentSession so that
    prompt preparation survives across inference calls.
    """

    agent: Agent

    run_context: RunContext

    conversation_context: ConversationContext

    prompt_state: PromptState
