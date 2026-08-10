from __future__ import annotations

from uuid import uuid4

from app.runtime.chat.context import ChatContext
from app.runtime.chat.message import ChatMessage
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
    - Own the ChatContext
    - Own the RunContext
    - Track the active AgentActivity
    - Execute conversations
    - Manage the lifetime of a conversation
    """

    def __init__(
        self,
        *,
        agent: Agent,
        chat_context: ChatContext | None = None,
    ) -> None:

        self._id = str(uuid4())

        self._agent = agent

        self._chat_context = (
            chat_context
            if chat_context is not None
            else ChatContext()
        )

        self._run_context = RunContext(
            session=self,
        )

        self._current_activity: AgentActivity | None = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def chat_context(self) -> ChatContext:
        return self._chat_context

    @property
    def run_context(self) -> RunContext:
        return self._run_context

    @property
    def current_activity(
        self,
    ) -> AgentActivity | None:
        return self._current_activity

    @property
    def messages(self) -> list[ChatMessage]:
        return self._chat_context.messages

    @property
    def last_message(self) -> ChatMessage | None:
        return self._chat_context.last

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

        The user message is appended to the
        conversation before invoking the runner.
        """

        self._chat_context.add(
            ChatMessage.user(
                message,
            )
        )

        return await self._agent.runner.run(
            self,
        )

    async def run_message(
        self,
        message: ChatMessage,
    ) -> LLMResponse:
        """
        Execute one conversational turn using an
        existing ChatMessage.
        """

        self._chat_context.add(
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
        Clear the conversation while preserving
        the session identity.
        """

        self._chat_context.clear()

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
