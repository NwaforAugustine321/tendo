from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.runtime.chat.message import ChatMessage
from app.runtime.events.events import (
    EventType,
    Status,
    StatusEvent,
)
from app.runtime.guardrails.exceptions import (
    RetryRequest,
)
from app.runtime.llm.response import LLMResponse
from app.runtime.middlewares.middleware import (
    AfterLLMEvent,
    AfterRunEvent,
    AfterToolsEvent,
    BeforeToolsEvent,
    ErrorEvent,
    MiddlewareEvent,
)
from app.runtime.prompts.builder import PromptBuilder
from app.runtime.prompts.context import PromptContext
from app.runtime.toolsets.executor import ToolExecutor

from .activity import AgentActivity
from .session import AgentSession

if TYPE_CHECKING:
    from app.runtime.agents.run_context import RunContext


logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Executes an AgentSession.

    Responsibilities
    ----------------
    - Coordinate middleware
    - Coordinate guardrails
    - Coordinate context optimization
    - Coordinate LLM execution
    - Coordinate tool execution

    The runner does NOT:

    - build prompts to measure their size
    - count tokens
    - decide the context threshold
    - perform conversation optimization itself

    Context monitoring is performed by RunContext through
    the session's ContextMonitor.

    Conversation optimization is delegated to
    ContextManager.
    """

    def __init__(
        self,
        *,
        tool_executor: ToolExecutor,
        max_iterations: int,
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

            await run_context.emitter.emit(
                EventType.PROGRESS,
                StatusEvent(
                    status=Status.STARTING,
                ),
            )

            await run_context.middleware.dispatch(
                MiddlewareEvent.BEFORE_RUN,
                run_context,
            )

            for iteration in range(
                self._max_iterations,
            ):

                try:

                    #
                    # Request guardrails.
                    #
                    blocked = (
                        await run_context.guardrails.check_request(
                            run_context,
                        )
                    )

                    if blocked is not None:

                        await run_context.emitter.emit(
                            EventType.PROGRESS,
                            StatusEvent(
                                status=Status.FAILED,
                            ),
                        )

                        assistant_message = (
                            ChatMessage.from_llm_response(
                                blocked,
                            )
                        )

                        run_context.add_message(
                            assistant_message,
                        )

                        return blocked

                    #
                    # Context preparation and optimization.
                    #
                    # Prepare the stable prompt first so the context measurement
                    # includes conversation, memory, RAG, instructions, output
                    # formatting, and template messages.
                    #
                    builder = PromptBuilder(
                        context=PromptContext(
                            agent=session.agent,
                            run_context=run_context,
                            conversation_context=(
                                session.conversation_context
                            ),
                            prompt_state=session.prompt_state,
                        ),
                    )

                    await builder.prepare()

                    run_context.refresh_context_threshold(
                        stable_messages=(
                            session.prompt_state.stable_messages
                        ),
                    )

                    logger.warning(
                        "PRE-INFERENCE CONTEXT CHECK: "
                        "tokens=%s threshold=%s reached=%s",
                        run_context.context_tokens,
                        session.context_monitor.threshold,
                        run_context.context_threshold_reached,
                    )

                    if run_context.context_threshold_reached:

                        await run_context.emitter.emit(
                            EventType.PROGRESS,
                            StatusEvent(
                                status=Status.ANALYZING,
                            ),
                        )

                        await self._optimize_context(
                            session=session,
                            run_context=run_context,
                        )

                    #
                    # Prepare for LLM execution.
                    #
                    await run_context.emitter.emit(
                        EventType.PROGRESS,
                        StatusEvent(
                            status=Status.PLANNING,
                        ),
                    )

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_LLM,
                        run_context,
                    )

                    #
                    # InferenceStream is responsible for
                    # constructing the actual prompt.
                    #
                    # The runner does not build the prompt.
                    #
                    stream = session.agent.llm.chat(
                        conversation_context=(
                            session.conversation_context
                        ),
                        run_context=run_context,
                    )

                    await run_context.emitter.emit(
                        EventType.PROGRESS,
                        StatusEvent(
                            status=Status.REASONING,
                        ),
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
                    # Response guardrails.
                    #
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

                        await run_context.emitter.emit(
                            EventType.PROGRESS,
                            StatusEvent(
                                status=Status.CANCELLED,
                            ),
                        )

                        continue

                    assistant_message = (
                        ChatMessage.from_llm_response(
                            response,
                        )
                    )

                    # Adding the message performs the next

                    run_context.add_message(
                        assistant_message,
                    )

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

                    #
                    # Tool execution.
                    #
                    await run_context.emitter.emit(
                        EventType.PROGRESS,
                        StatusEvent(
                            status=Status.USING_TOOL,
                        ),
                    )

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.BEFORE_TOOLS,
                        run_context,
                        BeforeToolsEvent(
                            tool_calls=response.tool_calls,
                        ),
                    )

                    results = (
                        await self._tool_executor.execute(
                            tool_calls=response.tool_calls,
                            ctx=run_context,
                        )
                    )

                    tool_messages = (
                        self._tool_executor.build_tool_messages(
                            results,
                        )
                    )

                    #
                    # Track tool messages.
                    run_context.add_messages(
                        tool_messages,
                    )

                    await run_context.middleware.dispatch(
                        MiddlewareEvent.AFTER_TOOLS,
                        run_context,
                        AfterToolsEvent(
                            messages=tool_messages,
                            results=results,
                        ),
                    )

                    remaining_steps = self._max_iterations - iteration
                    run_context.add_message(
                        ChatMessage.system(
                            f"You have {remaining_steps} interaction steps remaining. "
                            "Use them efficiently and complete the task within the limit."
                        ),
                    )
                except RetryRequest:

                    await run_context.emitter.emit(
                        EventType.PROGRESS,
                        StatusEvent(
                            status=Status.RETRYING,
                        ),
                    )

                    continue

            #
            # Maximum iterations reached.
            #
            if response is not None:
                return response

            await run_context.emitter.emit(
                EventType.PROGRESS,
                StatusEvent(
                    status=Status.MAX_ITERATION,
                ),
            )

            response = await self._force_final_response(
                session=session,
                run_context=run_context,
            )

            return response

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

    async def _optimize_context(
        self,
        *,
        session: AgentSession,
        run_context: RunContext,
    ) -> None:
        """
        Optimize the conversation after the ContextMonitor
        has detected that the threshold was reached.

        The token count was already calculated by RunContext.

        This method does not:

        - build a prompt for counting
        - count tokens again
        - perform optimization itself
        """

        builder = PromptBuilder(
            context=PromptContext(
                agent=session.agent,
                run_context=run_context,
                conversation_context=(
                    session.conversation_context
                ),
                prompt_state=session.prompt_state,
            ),
        )

        optimized = await (
            session.agent.context_manager.optimize(
                builder,
            )
        )

        # The next execution cycle will perform a fresh full
        # context measurement.
        #
        run_context.reset_context_threshold()

    async def _force_final_response(
        self,
        *,
        session: AgentSession,
        run_context: RunContext,
    ) -> LLMResponse:

        await run_context.emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.FINALIZING,
            ),
        )

        run_context.add_message(
            ChatMessage.system(
                "You have reached the maximum number of interaction steps.\n"
                "Stop taking further actions and provide your best final response based on the information gathered so far."

            ),
        )

        stream = session.agent.llm.chat(
            conversation_context=(
                session.conversation_context
            ),
            run_context=run_context,
        )

        await run_context.emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.REASONING,
            ),
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

        assistant_message = (
            ChatMessage.from_llm_response(
                response,
            )
        )

        run_context.add_message(
            assistant_message,
        )

        await run_context.middleware.dispatch(
            MiddlewareEvent.AFTER_LLM,
            run_context,
            AfterLLMEvent(
                message=assistant_message,
                response=response,
            ),
        )

        return response
