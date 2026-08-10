from __future__ import annotations

from app.runtime.guardrails.exceptions import (
    GuardrailViolation,
    RetryRequest,
)
from app.runtime.agents.middleware import MiddlewareEvent
from app.runtime.chat.message import ChatMessage
from app.runtime.llm.response import LLMResponse
from app.runtime.toolsets.executor import ToolExecutor

from .activity import AgentActivity
from .session import AgentSession


class AgentRunner:
    """
    Executes an AgentSession.

    Responsibilities
    ----------------
    - Coordinate LLM execution
    - Coordinate middleware
    - Coordinate guardrails
    - Coordinate tool execution
    - Update the ChatContext
    """

    def __init__(
        self,
        *,
        tool_executor: ToolExecutor,
        max_iterations: int = 20,
    ) -> None:

        self._tool_executor = tool_executor
        self._max_iterations = max_iterations

    async def run(
        self,
        session: AgentSession,
    ) -> LLMResponse:

        chat_context = session.chat_context
        run_context = session.run_context
        run_context.clear_current_messages()

        response: LLMResponse | None = None

        try:

            await run_context.middleware.dispatch(
                MiddlewareEvent.BEFORE_RUN,
                run_context,
            )

            for _ in range(self._max_iterations):

                try:

                    await run_context.guardrails.check_request(
                        run_context,
                    )

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_LLM,
                        run_context,
                    )

                    stream = session.agent.llm.chat(
                        ctx=chat_context,
                        run_context=run_context,
                    )

                    activity = AgentActivity(
                        stream=stream,
                    )

                    session.set_current_activity(
                        activity,
                    )

                    try:
                        response = await activity.wait()
                    finally:
                        session.clear_activity()

                    response = (
                        await run_context.guardrails.check_response(
                            run_context,
                            response,
                        )
                    )

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.AFTER_LLM,
                        run_context,
                        response,
                    )

                    assistant_message = ChatMessage.from_llm_response(
                        response,
                    )

                    chat_context.add(
                        assistant_message,
                    )

                    run_context.add_current_message(
                        assistant_message,
                    )

                    if not response.has_tool_calls:
                        return response

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_TOOLS,
                        run_context,
                        response.tool_calls,
                    )

                    results = await self._tool_executor.execute(
                        tool_calls=response.tool_calls,
                        ctx=run_context,
                    )

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.AFTER_TOOLS,
                        run_context,
                        results,
                    )

                    tool_messages = (
                        self._tool_executor.build_tool_messages(
                            results,
                        )
                    )

                    chat_context.extend(
                        tool_messages,
                    )

                    run_context.add_current_messages(
                        tool_messages,
                    )

                except RetryRequest:
                    continue

            raise RuntimeError(
                "Maximum tool iterations exceeded."
            )

        except Exception as error:

            await run_context.middleware.dispatch(
                MiddlewareEvent.ON_ERROR,
                run_context,
                error,
            )

            raise

        finally:

            await run_context.middleware.dispatch(
                MiddlewareEvent.AFTER_RUN,
                run_context,
                response,
            )

            if (
                response is not None
                and session.agent.memory is not None
            ):
                try:

                    await session.agent.memory.reflect(
                        run_context,
                    )

                except Exception as error:

                    logger.exception(
                        "Memory reflection failed.",
                        exc_info=error,
                    )
