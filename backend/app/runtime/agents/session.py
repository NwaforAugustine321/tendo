from __future__ import annotations

from uuid import uuid4

from app.runtime.chat.message import ChatMessage
from app.runtime.conversation.context import (
    ConversationContext,
)
from app.runtime.llm.response import LLMResponse

from .activity import AgentActivity
from .agent import Agent
from .run_context import RunContext


class AgentSession:
    """
    Represents one active conversation with an Agent.

    A session owns all mutable runtime state.

    Responsibilities
    ----------------
    - Own the ConversationContext
    - Own the RunContext
    - Track the active AgentActivity
    - Execute conversations
    - Manage the lifetime of a conversation
    """

    def __init__(
        self,
        *,
        agent: Agent,
        conversation_context: ConversationContext | None = None,
    ) -> None:

        self._id = str(uuid4())

        self._agent = agent

        self._conversation_context = (
            conversation_context
            if conversation_context is not None
            else ConversationContext(
                conversation_id=self._id,
            )
        )

        self._run_context = RunContext(
            session=self,
        )

        self._current_activity: AgentActivity | None = None

    @property
    def id(
        self,
    ) -> str:
        return self._id

    @property
    def agent(
        self,
    ) -> Agent:
        return self._agent

    @property
    def conversation_context(
        self,
    ) -> ConversationContext:
        """
        Loaded conversation history.
        """

        return self._conversation_context

    @property
    def run_context(
        self,
    ) -> RunContext:
        """
        Current execution context.
        """

        return self._run_context

    @property
    def current_activity(
        self,
    ) -> AgentActivity | None:
        return self._current_activity

    @property
    def running(
        self,
    ) -> bool:

        return (
            self._current_activity is not None
            and not self._current_activity.finished
        )

    async def run(
        self,
        message: str,
    ) -> LLMResponse:
        """
        Execute one conversational turn.
        """

        return await self.run_message(
            ChatMessage.user(
                message,
            )
        )

    async def run_message(
        self,
        message: ChatMessage,
    ) -> LLMResponse:
        """
        Execute one conversational turn.
        """

        #
        # Start a new execution.
        #
        self._run_context.start(
            message,
        )

        return await self._agent.runner.run(
            self,
        )

    def set_current_activity(
        self,
        activity: AgentActivity,
    ) -> None:

        self._current_activity = activity

    def clear_activity(
        self,
    ) -> None:

        self._current_activity = None

    def reset(
        self,
    ) -> None:
        """
        Reset the session while preserving
        the session identity.
        """

        self._conversation_context = ConversationContext(
            conversation_id=self.id,
        )

        self._run_context = RunContext(
            session=self,
        )

        self._current_activity = None

    async def aclose(
        self,
    ) -> None:
        """
        Cancel any running activity.
        """

        if self._current_activity is not None:
            await self._current_activity.cancel()

        self._current_activity = None
