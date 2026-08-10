from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from app.runtime.chat.context import ChatContext

if TYPE_CHECKING:
    from .agent import Agent
    from .session import AgentSession


@dataclass(slots=True)
class RunContext:
    """
    Context shared across every tool call during an AgentSession.

    This object is passed to tools so they can access the
    current conversation and agent state.

    RunContext does not own any state. It provides access to
    the current AgentSession and convenient shortcuts.
    """

    session: AgentSession

    @property
    def middleware(
        self,
    ):
        return self.agent.middleware

    @property
    def guardrails(
        self,
    ):
        """
        Agent guardrail manager.
        """
        return self.agent.guardrails

    @property
    def agent(self) -> Agent:
        """
        The agent executing this run.
        """
        return self.session.agent

    @property
    def chat_context(self) -> ChatContext:
        """
        The current conversation.
        """
        return self.session.chat_context

    @property
    def session_id(self) -> str:
        """
        Unique identifier for the current session.
        """
        return self.session.id

    @property
    def metadata(self) -> dict[str, Any]:
        """
        Optional session metadata.

        Reserved for future use.
        """
        return {}
