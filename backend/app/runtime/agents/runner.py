from __future__ import annotations

import logging

from app.runtime.middlewares.middleware import (
    AfterLLMEvent,
    AfterRunEvent,
    AfterToolsEvent,
    BeforeToolsEvent,
    ErrorEvent,
    MiddlewareEvent,
)
from app.runtime.chat.message import ChatMessage
from app.runtime.guardrails.exceptions import (
    RetryRequest,
)
from app.runtime.llm.response import LLMResponse
from app.runtime.toolsets.executor import ToolExecutor

from .activity import AgentActivity
from .session import AgentSession

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Executes an AgentSession.

    Responsibilities
    ----------------
    - Coordinate middleware
    - Coordinate guardrails
    - Coordinate LLM execution
    - Coordinate tool execution
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

        run_context = session.run_context

        response: LLMResponse | None = None

        try:

            #
            # BEFORE_RUN
            #
            # ConversationMiddleware persists the
            # current user message here.
            #
            await run_context.middleware.dispatch(
                MiddlewareEvent.BEFORE_RUN,
                run_context,
            )

            for _ in range(
                self._max_iterations,
            ):

                try:

                    blocked = (
                        await run_context.guardrails.check_request(
                            run_context,
                        )
                    )

                    if blocked is not None:

                        assistant_message = (
                            ChatMessage.from_llm_response(
                                blocked
                            )
                        )

                        run_context.add_message(
                            assistant_message,
                        )

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_LLM,
                        run_context,
                    )

                    stream = session.agent.llm.chat(
                        conversation_context=session.conversation_context,
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

                    checked_response = (
                        await run_context.guardrails.check_response(
                            run_context,
                            response,
                        )
                    )

                    if checked_response is not None:
                        assistant_message = (
                            ChatMessage.from_llm_response(
                                checked_response,
                            )
                        )

                        run_context.add_message(
                            assistant_message,
                        )

                        continue

                    assistant_message = (
                        ChatMessage.from_llm_response(
                            response,
                        )
                    )

                    #
                    # Track current execution.
                    #
                    run_context.add_message(
                        assistant_message,
                    )

                    #
                    # ConversationMiddleware persists
                    # the assistant message here.
                    #
                    await run_context.middleware.dispatch(
                        MiddlewareEvent.AFTER_LLM,
                        run_context,
                        AfterLLMEvent(
                            message=assistant_message,
                            response=response,
                        ),
                    )

                    #
                    # Finished?
                    #
                    if not response.has_tool_calls:
                        return response

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_TOOLS,
                        run_context,
                        BeforeToolsEvent(
                            tool_calls=response.tool_calls,
                        ),
                    )

                    results = await self._tool_executor.execute(
                        tool_calls=response.tool_calls,
                        ctx=run_context,
                    )

                    tool_messages = (
                        self._tool_executor.build_tool_messages(
                            results,
                        )
                    )

                    #
                    # Track current execution.
                    #
                    run_context.add_messages(
                        tool_messages,
                    )

                    #
                    # ConversationMiddleware persists
                    # tool messages here.
                    #
                    await run_context.middleware.dispatch(
                        MiddlewareEvent.AFTER_TOOLS,
                        run_context,
                        AfterToolsEvent(
                            messages=tool_messages,
                            results=results,
                        ),
                    )

                except RetryRequest:
                    continue

            if response is not None:
                return response

            return await self._force_final_response(
                session=session,
                run_context=run_context,
            )

        except Exception as error:

            await run_context.middleware.dispatch(
                MiddlewareEvent.ON_ERROR,
                run_context,
                ErrorEvent(
                    error=error,
                ),
            )

            raise

        finally:

            await run_context.middleware.dispatch(
                MiddlewareEvent.AFTER_RUN,
                run_context,
                AfterRunEvent(
                    response=response,
                ),
            )

            if (
                response is not None
                and session.agent.memory is not None
            ):
                try:

                    await session.agent.memory.reflect(
                        run_context,
                    )

                except Exception:

                    logger.exception(
                        "Memory reflection failed.",
                    )

    async def _force_final_response(
        self,
        *,
        session,
        run_context,
    ) -> LLMResponse:

        run_context.add_message(
            ChatMessage.system(
                "You have reached the maximum number of tool iterations. "
                "Provide your best final response to the user now based on "
                "the information gathered so far. Do not call any more tools."
            )
        )

        stream = session.agent.llm.chat(
            conversation_context=session.conversation_context,
            run_context=run_context,
        )

        activity = AgentActivity(
            stream=stream,
        )

        session.set_current_activity(activity)

        try:
            response = await activity.wait()
        finally:
            session.clear_activity()

        assistant_message = ChatMessage.from_llm_response(response)
        run_context.add_message(assistant_message)

        await run_context.middleware.dispatch(
            MiddlewareEvent.AFTER_LLM,
            run_context,
            AfterLLMEvent(
                message=assistant_message,
                response=response,
            ),
        )

        return response
