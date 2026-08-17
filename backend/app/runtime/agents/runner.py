from __future__ import annotations

import json
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
from app.runtime.toolsets.tool_use_call import ToolUseCall

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

        self._max_reasoning_only_attempts = 2
        self._max_final_response_attempts = 2

    async def run(
        self,
        session: AgentSession,
    ) -> LLMResponse:

        run_context = session.run_context

        response: LLMResponse | None = None

        reasoning_only_attempts = 0

        tool_usage = ToolUseCall()

        pending_tools: list[str] = []

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
                        # The LLM produced a final response.
                        #
                        # Any tool results still pending at this point
                        # were sufficient for the model to complete the
                        # task.
                        #

                        if response.text:

                            reasoning_only_attempts = 0

                            for tool_name in pending_tools:

                                tool_usage.record_result(
                                    tool_name,
                                    tool_usage.last_tool_result,
                                    useful=True,
                                )

                            pending_tools.clear()

                            return response

                        #
                        # Model produced neither text nor tools.
                        #

                        reasoning_only_attempts += 1

                        logger.warning(
                            "[RUNNER] Reasoning-only response. "
                            "Attempt %d/%d at interaction step %d/%d.",
                            reasoning_only_attempts,
                            self._max_reasoning_only_attempts,
                            current_step,
                            self._max_iterations,
                        )

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
                                "steps remaining.\n"
                                "You have not produced a response or tool call. "
                                "Do not continue reasoning without producing output. "
                                "Either execute the next required action or provide "
                                "the user-facing final response."
                            ),
                        )

                        continue

                    #
                    # The LLM produced another tool call.
                    #
                    # This means the previous tool result was not enough
                    # to complete the task.
                    #

                    reasoning_only_attempts = 0

                    for tool_name in pending_tools:

                        tool_usage.record_result(
                            tool_name,
                            tool_usage.last_tool_result,
                            useful=False,
                        )

                    pending_tools.clear()

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

                    #
                    # Validate and execute tool calls.
                    #

                    executable_calls = []
                    blocked_calls = []

                    for tool_call in response.tool_calls:

                        tracking_name = (
                            tool_usage.tracking_tool_name(
                                tool_call.name,
                                tool_call.arguments,
                            )
                        )

                        tracking_arguments = (
                            tool_usage.tracking_arguments(
                                tool_call.name,
                                tool_call.arguments,
                            )
                        )

                        #
                        # tool_search has a separate query limit.
                        #

                        if tool_call.name == "tool_search":

                            query = tool_usage.extract_search_query(
                                tool_call.arguments,
                            )

                            #
                            # Once discovery has returned executable tools,
                            # do not spend another iteration rediscovering them.
                            # The LLM must use call_tool with the discovered
                            # capability instead.
                            #
                            if tool_usage.discovered_tools:
                                logger.warning(
                                    "[RUNNER] tool_search blocked after "
                                    "tools were discovered: query=%r tools=%s",
                                    query,
                                    sorted(
                                        tool_usage.discovered_tools,
                                    ),
                                )

                                blocked_calls.append(
                                    (
                                        tool_call,
                                        (
                                            "Tool discovery has already "
                                            "completed for this request. "
                                            "Use call_tool to execute one "
                                            "of the discovered tools instead "
                                            "of calling tool_search again. "
                                            "If a previous tool result was "
                                            "insufficient, change the query "
                                            "or use another discovered tool."
                                        ),
                                    ),
                                )

                                continue

                            if not tool_usage.can_search(
                                query,
                            ):

                                logger.warning(
                                    "[RUNNER] tool_search blocked: "
                                    "query=%r search_count=%d",
                                    query,
                                    tool_usage.search_count(query),
                                )

                                blocked_calls.append(
                                    (
                                        tool_call,
                                        (
                                            "Tool search limit reached for "
                                            "this query. Do not repeat the "
                                            "same search. Use the tools that "
                                            "have already been discovered or "
                                            "change the search query."
                                        ),
                                    ),
                                )

                                continue

                            tool_usage.record_search(
                                query,
                            )

                        #
                        # Prevent exact duplicate tool execution.
                        #

                        if tool_usage.has_executed(
                            tracking_name,
                            tracking_arguments,
                        ):

                            logger.warning(
                                "[RUNNER] Duplicate tool execution blocked: "
                                "tool=%s arguments=%s",
                                tracking_name,
                                tracking_arguments,
                            )

                            blocked_calls.append(
                                (
                                    tool_call,
                                    (
                                        "This exact tool call has already "
                                        "been executed. Do not repeat the "
                                        "same tool with the same arguments. "
                                        "Change the query or use another "
                                        "available tool."
                                    ),
                                ),
                            )

                            continue

                        tool_usage.record_execution(
                            tracking_name,
                            tracking_arguments,
                        )

                        executable_calls.append(
                            tool_call,
                        )

                    #
                    # Execute allowed calls.
                    #

                    results = []

                    if executable_calls:

                        results = (
                            await self._tool_executor.execute(
                                tool_calls=executable_calls,
                                ctx=run_context,
                            )
                        )

                    #
                    # Build normal tool messages.
                    #

                    tool_messages = (
                        self._tool_executor.build_tool_messages(
                            results,
                        )
                    )

                    #
                    # Build messages for blocked duplicate/limited calls.
                    #

                    for tool_call, message in blocked_calls:

                        tool_messages.append(
                            ChatMessage.tool(
                                tool_call_id=tool_call.id,
                                name=tool_call.name,
                                content=message,
                            )
                        )

                    run_context.add_messages(
                        tool_messages,
                    )

                    #
                    # Track discovered capabilities and tools whose results
                    # are now pending evaluation by the LLM.
                    #

                    for result in results:

                        if result.tool_call.name == "tool_search":

                            discovered_tools = (
                                tool_usage.extract_discovered_tools(
                                    result.output,
                                )
                            )

                            if discovered_tools:
                                tool_usage.record_discovered_tools(
                                    discovered_tools,
                                )

                                logger.info(
                                    "[RUNNER] Discovered tools: %s",
                                    sorted(
                                        tool_usage.discovered_tools,
                                    ),
                                )

                        tracking_name = (
                            tool_usage.tracking_tool_name(
                                result.tool_call.name,
                                result.tool_call.arguments,
                            )
                        )

                        pending_tools.append(
                            tracking_name,
                        )

                        tool_usage.last_tool_result = (
                            result.output
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
                    # Tool-use guidance.
                    #

                    run_context.add_message(
                        ChatMessage.system(
                            tool_usage.build_tool_usage_guidance(),
                        ),
                    )

                    #
                    # Runtime step guidance.
                    #

                    urgency = tool_usage.runtime_step_guidance(
                        remaining_steps=remaining_steps,
                        max_iterations=self._max_iterations,
                    )

                    if urgency:
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

            await run_context.emitter.emit(
                EventType.PROGRESS,
                StatusEvent(
                    status=Status.COMPLETED,
                ),
            )

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
