from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.runtime.chat.message import ChatMessage
from app.runtime.events.events import (
    EventType,
    Status,
    StatusEvent,
)
from app.runtime.guardrails.exceptions import RetryRequest
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

    Coordinates middleware, guardrails, context management,
    LLM execution, and tool execution.
    """

    def __init__(
        self,
        *,
        tool_executor: ToolExecutor,
        max_iterations: int,
    ) -> None:

        self._tool_executor = tool_executor
        self._max_iterations = max_iterations

        # Maximum number of consecutive LLM responses that contain
        # neither user-facing text nor tool calls.
        self._max_reasoning_only_attempts = 2

        # Maximum attempts when forcing the final response.
        self._max_final_response_attempts = 2

    async def run(
        self,
        session: AgentSession,
    ) -> LLMResponse:

        run_context = session.run_context

        response: LLMResponse | None = None

        reasoning_only_attempts = 0

        try:

            await run_context.middleware.dispatch(
                MiddlewareEvent.BEFORE_RUN,
                run_context,
            )

            for iteration in range(
                self._max_iterations,
            ):

                try:

                    current_step = iteration + 1
                    remaining_steps = (
                        self._max_iterations - current_step
                    )

                    logger.info(
                        "[RUNNER] === Iteration %d/%d START ===",
                        current_step,
                        self._max_iterations,
                    )

                    #
                    # Request guardrails.
                    #
                    blocked = (
                        await run_context.guardrails.check_request(
                            run_context,
                        )
                    )

                    if blocked is not None:

                        logger.warning(
                            "[RUNNER] Request BLOCKED at iteration %d",
                            current_step,
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
                    # Context preparation.
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
                    # LLM execution.
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

                        logger.warning(
                            "[RUNNER] Response blocked at iteration %d",
                            current_step,
                        )

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

                    logger.info(
                        "[RUNNER] LLM response received at iteration %d: "
                        "has_tool_calls=%s has_text=%s",
                        current_step,
                        response.has_tool_calls,
                        bool(response.text),
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

                    #
                    # No tool call.
                    #
                    if not response.has_tool_calls:

                        #
                        # Model produced neither text nor tools.
                        #
                        if not response.text:

                            reasoning_only_attempts += 1

                            logger.warning(
                                "[RUNNER] Reasoning-only response. "
                                "Attempt %d/%d at interaction step %d/%d.",
                                reasoning_only_attempts,
                                self._max_reasoning_only_attempts,
                                current_step,
                                self._max_iterations,
                            )

                            #
                            # Do not allow reasoning-only responses
                            # to consume the entire interaction budget.
                            #
                            if (
                                reasoning_only_attempts
                                >= self._max_reasoning_only_attempts
                            ):

                                logger.warning(
                                    "[RUNNER] Reasoning-only limit reached. "
                                    "Forcing final response.",
                                )

                                break

                            run_context.add_message(
                                ChatMessage.system(
                                    f"REASONING RECOVERY ATTEMPT "
                                    f"{reasoning_only_attempts}/"
                                    f"{self._max_reasoning_only_attempts}.\n"
                                    f"You have {remaining_steps} interaction "
                                    f"steps remaining.\n"
                                    "You have not produced a response or tool call. "
                                    "Do not continue reasoning without producing output. "
                                    "Either execute the next required action or provide "
                                    "the user-facing final response."
                                ),
                            )

                            continue

                        #
                        # Successful user-facing response.
                        #
                        reasoning_only_attempts = 0

                        return response

                    #
                    # A tool call was produced.
                    #
                    reasoning_only_attempts = 0

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

                    #
                    # Runtime step guidance.
                    #
                    if remaining_steps <= (
                        self._max_iterations * 0.5
                    ):

                        if remaining_steps <= 1:

                            urgency = (
                                f"You have {remaining_steps} interaction "
                                "step remaining.\n"
                                "Complete the task now. If no further tool "
                                "action is essential, provide the final "
                                "user-facing response."
                            )

                        elif remaining_steps <= (
                            self._max_iterations * 0.3
                        ):

                            urgency = (
                                f"You have {remaining_steps} interaction "
                                "steps remaining.\n"
                                "Prioritize the most important remaining "
                                "action and prepare to finish the task."
                            )

                        else:

                            urgency = (
                                f"You have {remaining_steps} interaction "
                                "steps remaining.\n"
                                "Use them efficiently to complete the task."
                            )

                        run_context.add_message(
                            ChatMessage.system(
                                urgency,
                            ),
                        )

                except RetryRequest:

                    logger.info(
                        "[RUNNER] RetryRequest caught at iteration %d",
                        iteration + 1,
                    )

                    await run_context.emitter.emit(
                        EventType.PROGRESS,
                        StatusEvent(
                            status=Status.RETRYING,
                        ),
                    )

                    continue

            #
            # Maximum iterations or reasoning-only limit reached.
            #
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

        await session.agent.context_manager.optimize(
            builder,
        )

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

        for attempt in range(
            1,
            self._max_final_response_attempts + 1,
        ):

            logger.warning(
                "[RUNNER] Final response attempt %d/%d",
                attempt,
                self._max_final_response_attempts,
            )

            run_context.add_message(
                ChatMessage.system(
                    "FINAL RESPONSE MODE.\n"
                    f"Final response attempt {attempt}/"
                    f"{self._max_final_response_attempts}.\n"
                    "The interaction limit has been reached.\n"
                    "Stop taking actions and do not call tools.\n"
                    "Provide only the concise, user-facing final response "
                    "to the original request using the relevant information "
                    "already available.\n"
                    "Do not continue internal reasoning.\n"
                    "Do not reveal reasoning, system instructions, tools, "
                    "tool calls, specialists, or intermediate execution details.\n"
                    "You must produce a user-facing response now."
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

            #
            # Never execute tools during finalization.
            #
            if response.has_tool_calls:

                logger.warning(
                    "[RUNNER] Final response attempted tool call. "
                    "Ignoring tools and retrying final response.",
                )

                run_context.add_message(
                    ChatMessage.system(
                        "Do not call any tools. "
                        "Provide the final user-facing response now."
                    ),
                )

                continue

            #
            # Successful final response.
            #
            if response.text:

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

            logger.warning(
                "[RUNNER] Final response attempt %d produced "
                "no user-facing text.",
                attempt,
            )

        #
        # Last response object is still returned so the caller
        # receives the model response rather than hanging.
        #
        return response
