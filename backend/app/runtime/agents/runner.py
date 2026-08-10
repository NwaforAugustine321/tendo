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

        response: LLMResponse | None = None

        try:

            await run_context.middleware.dispatch(
                MiddlewareEvent.BEFORE_RUN,
                run_context,
            )

            for _ in range(self._max_iterations):

                try:

                    #
                    # Input guardrails.
                    #
                    await run_context.guardrails.check_request(
                        run_context,
                    )

                    #
                    # Before LLM middleware.
                    #
                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_LLM,
                        run_context,
                    )

                    #
                    # Execute the model.
                    #
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

                    #
                    # Output guardrails.
                    #
                    response = (
                        await run_context.guardrails.check_response(
                            run_context,
                            response,
                        )
                    )

                    #
                    # Middleware observes the approved response.
                    #
                    await run_context.middleware.dispatch(
                        MiddlewareEvent.AFTER_LLM,
                        run_context,
                        response,
                    )

                    #
                    # Persist assistant message.
                    #
                    chat_context.add(
                        ChatMessage.from_llm_response(
                            response
                        )

                    )

                    #
                    # Finished.
                    #
                    if not response.has_tool_calls:
                        return response

                    #
                    # Before tool execution.
                    #
                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_TOOLS,
                        run_context,
                        response.tool_calls,
                    )

                    results = await self._tool_executor.execute(
                        tool_calls=response.tool_calls,
                        ctx=run_context,
                    )

                    #
                    # After tool execution.
                    #
                    await run_context.middleware.dispatch(
                        MiddlewareEvent.AFTER_TOOLS,
                        run_context,
                        results,
                    )

                    chat_context.extend(
                        self._tool_executor.build_tool_messages(
                            results,
                        )
                    )

                except RetryRequest:
                    #
                    # Restart the current iteration.
                    #
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
