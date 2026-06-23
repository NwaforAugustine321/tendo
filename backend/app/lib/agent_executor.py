"""Agent executor — manages the execution loop for agent task processing.

Based on CrewAI's AgentExecutor pattern: holds references to LLM, tools,
prompt, and agent config, then drives the ReAct loop until a final answer
is produced or max iterations are reached.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from app.lib.i18n import _get_i18n
from app.lib.prompts import StandardPromptResult, SystemPromptResult

logger = logging.getLogger(__name__)


def _slice(key: str) -> str:
    """Get a raw prompt slice template from translations."""
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")


class AgentExecutor(BaseModel):
    """Agent Executor that drives the ReAct execution loop.

    Holds all context needed to run an agent's task: the LLM, tools,
    prompt templates, stop words, and iteration limits.

    Supports human-in-the-loop feedback: when `ask_for_human_input` is True,
    the executor will pause after producing a final answer, collect feedback,
    inject it back into messages, and re-run the loop until the human approves.

    Usage:
        executor = AgentExecutor(
            llm=llm,
            task=task,
            agent=agent,
            crew=crew,
            tools=parsed_tools,
            prompt=prompt,
            original_tools=raw_tools,
            stop_words=stop_words,
            max_iter=25,
            tools_handler=tools_handler,
            tools_names=get_tool_names(parsed_tools),
            tools_description=render_text_description_and_args(parsed_tools),
            respect_context_window=True,
            request_within_rpm_limit=rpm_limit_fn,
            response_model=MyOutputModel,
            ask_for_human_input=True,
            human_input_fn=my_input_handler,
        )
        result = await executor.invoke(task_prompt)
    """

    llm: Any = Field(description="The LLM instance to use for generation")
    task: Any = Field(default=None, description="The task being executed")
    agent: Any = Field(description="The agent performing the task")
    crew: Any = Field(default=None, description="The crew context if applicable")
    tools: list[Any] = Field(default_factory=list, description="Tools available to the agent")
    prompt: SystemPromptResult | StandardPromptResult | None = Field(
        default=None, description="The constructed prompt for task execution"
    )
    stop_words: list[str] = Field(
        default_factory=list, description="Stop words for the LLM"
    )
    max_iter: int = Field(default=25, description="Maximum iterations for the ReAct loop")
    tools_handler: Any = Field(
        default=None, description="Handler for tool execution tracking"
    )
    tools_names: str = Field(default="", description="Comma-separated tool names")
    tools_description: str = Field(
        default="", description="Rendered tool descriptions with args"
    )
    respect_context_window: bool = Field(
        default=True, description="Whether to handle context window overflow"
    )
    request_within_rpm_limit: Callable[[], bool] | None = Field(
        default=None, description="RPM limiter function"
    )
    response_model: type[BaseModel] | None = Field(
        default=None, description="Pydantic model for structured output"
    )
    ask_for_human_input: bool = Field(
        default=False,
        description="Whether to pause for human feedback after final answer",
    )
    human_input_fn: Callable[[str], str] | None = Field(
        default=None,
        description="Async or sync function to collect human feedback. "
        "Receives the agent's current answer, returns feedback string. "
        "Empty string means human approves.",
    )
    status_callback: Any | None = Field(
        default=None,
        description="Async callable that receives status updates during execution. "
        "Called with a string like 'Checking information...' or 'Preparing response...'",
    )

    # Internal state
    _messages: list[dict[str, Any]] = PrivateAttr(default_factory=list)
    _iterations: int = PrivateAttr(default=0)

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Get the message history."""
        return self._messages

    @messages.setter
    def messages(self, value: list[dict[str, Any]]) -> None:
        """Set the message history."""
        self._messages = value

    @property
    def iterations(self) -> int:
        """Get the current iteration count."""
        return self._iterations

    async def _emit_status(self, text: str) -> None:
        """Emit a status update via the callback if configured."""
        if self.status_callback:
            try:
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(self.status_callback):
                    await self.status_callback(text)
                else:
                    await asyncio.to_thread(self.status_callback, text)
            except Exception:
                pass

    @staticmethod
    def _extract_thought(content: str) -> str:
        """Extract 'Thought:' text from agent ReAct format output."""
        if not content or "Thought:" not in content:
            return ""
        try:
            idx = content.index("Thought:")
            after = content[idx + 8:].strip()
            for marker in ["Action:", "Final Answer:", "\n\n"]:
                pos = after.find(marker)
                if pos != -1:
                    after = after[:pos].strip()
                    break
            return after[:200] if after else ""
        except (ValueError, IndexError):
            return ""

    def _build_initial_messages(self, task_prompt: str) -> list[dict[str, Any]]:
        """Build the initial message list from the prompt and task.

        Args:
            task_prompt: The assembled task prompt string.

        Returns:
            List of messages ready for LLM invocation.
        """
        messages: list[dict[str, Any]] = []

        if self.prompt and isinstance(self.prompt, SystemPromptResult):
            # System prompt mode: separate system and user messages
            system_content = self.prompt.system
            if self.tools_names:
                system_content = system_content.replace(
                    "{tools}", self.tools_description
                ).replace("{tool_names}", self.tools_names)
            messages.append({"role": "system", "content": system_content})

            user_content = self.prompt.user
            user_content = user_content.replace("{input}", task_prompt)
            messages.append({"role": "user", "content": user_content})
        elif self.prompt:
            # Standard mode: single prompt with all content
            content = self.prompt.prompt
            if self.tools_names:
                content = content.replace(
                    "{tools}", self.tools_description
                ).replace("{tool_names}", self.tools_names)
            content = content.replace("{input}", task_prompt)
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": task_prompt})

        return messages

    def _format_feedback_message(self, feedback: str) -> dict[str, Any]:
        """Format human feedback as a message for the LLM.

        Uses the "feedback_instructions" i18n slice with {feedback} placeholder.
        _format_feedback_message → format_message_for_llm pattern.

        Args:
            feedback: The human feedback string.

        Returns:
            A message dict with role "user" and formatted content.
        """
        content = _slice("feedback_instructions").format(feedback=feedback)
        return {"role": "user", "content": content.rstrip()}

    async def _handle_human_feedback(self, final_answer: str) -> str:
        """Process human feedback loop until human approves.

        Feedback handling:
        1. Present answer to human via human_input_fn
        2. If feedback is empty → human approves, return answer
        3. If feedback provided → inject feedback message, re-run loop
        4. Repeat until approved

        Args:
            final_answer: The agent's current final answer.

        Returns:
            The final approved answer after all feedback rounds.
        """
        if not self.human_input_fn:
            return final_answer

        import asyncio
        import inspect

        current_answer = final_answer

        while self.ask_for_human_input:
            # Collect feedback from human
            if inspect.iscoroutinefunction(self.human_input_fn):
                feedback = await self.human_input_fn(current_answer)
            else:
                feedback = await asyncio.to_thread(self.human_input_fn, current_answer)

            if not feedback or feedback.strip() == "":
                # Human approves — stop the feedback loop
                self.ask_for_human_input = False
            else:
                # Inject feedback and re-run the loop
                self._messages.append(self._format_feedback_message(feedback))
                current_answer = await self._invoke_loop()

        return current_answer

    async def _invoke_loop(self) -> str:
        """Run the LLM invocation loop from current messages state.

        Used internally for re-invocation after human feedback.
        Mirrors CrewAI's _invoke_loop pattern.

        When the agent returns a structured JSON response with
        workflow_status "waiting_for_user", the loop exits immediately
        so the graph node can send the question/fields to the user.
        The graph checkpointer handles resumption on next user message.

        If context length is exceeded and respect_context_window is True,
        messages are summarized and the loop retries.

        Returns:
            The agent's final answer string.
        """
        from app.lib.context_handler import handle_context_length, is_context_length_exceeded

        iterations_left = self.max_iter - self._iterations

        for _ in range(max(iterations_left, 1)):
            self._iterations += 1

            # Enforce RPM limit if configured
            if self.request_within_rpm_limit:
                self.request_within_rpm_limit()

            # Call LLM
            try:
                response = await self.llm.ainvoke(self._messages)
            except Exception as e:
                if is_context_length_exceeded(e):
                    await handle_context_length(
                        messages=self._messages,
                        respect_context_window=self.respect_context_window,
                    )
                    # Retry after summarization
                    continue
                raise

            # Check for tool calls
            if response.tool_calls:
                await self._emit_status("Checking information...")
                self._messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.tool_calls,
                })

                for tc in response.tool_calls:
                    tool_result = await self._execute_tool(tc)
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(tool_result),
                    })
                    # If tool returned a routing signal, stop immediately
                    if "__ROUTE__:" in str(tool_result):
                        await self._emit_status("delegating to co-workers...")
                        return str(tool_result)
                    # If tool returned a waiting-for-user signal, stop immediately
                    if "__WAITING__|" in str(tool_result):
                        return str(tool_result)
                continue

            # No tool calls — check for structured output
            await self._emit_status("Preparing response...")
            raw = response.content.strip() if response.content else ""

            # Extract and emit thought text if present
            thought = self._extract_thought(raw)
            if thought:
                await self._emit_status(f"__THOUGHT__:{thought}")

            # Detect workflow_status in agent output — if waiting_for_user,
            # return immediately without further processing
            if self._is_waiting_for_user(raw):
                return raw

            return raw

        # Max iterations — force final answer
        force_msg = _slice("force_final_answer")
        self._messages.append({"role": "user", "content": force_msg})
        response = await self.llm.ainvoke(self._messages)
        return response.content.strip() if response.content else ""

    def _is_waiting_for_user(self, raw: str) -> bool:
        """Check if the agent output indicates it's waiting for user input.

        Detects either:
        - workflow_status "waiting_for_user" in JSON output
        - __WAITING__| signal from ask_user_question tool

        Args:
            raw: The raw agent output string.

        Returns:
            True if the agent is waiting for user input.
        """
        # Check for __WAITING__ tool signal
        if "__WAITING__|" in raw:
            return True

        try:
            import json as _json
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            start = clean.find("{")
            if start == -1:
                return False
            depth = 0
            for i in range(start, len(clean)):
                if clean[i] == "{":
                    depth += 1
                elif clean[i] == "}":
                    depth -= 1
                    if depth == 0:
                        data = _json.loads(clean[start: i + 1])
                        return data.get("workflow_status") == "waiting_for_user"
            return False
        except (ValueError, KeyError, TypeError):
            return False

    async def invoke(self, task_prompt: str) -> str:
        """Execute the agent loop until a final answer is produced.

        Drives the ReAct loop:
        1. Send messages to LLM
        2. If LLM calls tools -> execute tools, append results, continue
        3. If LLM produces final answer -> check for human feedback
        4. If workflow_status is "waiting_for_user" -> return immediately (no feedback loop)
        5. If max_iter reached -> force final answer

        Args:
            task_prompt: The fully assembled task prompt.

        Returns:
            The agent's final answer string.
        """
        self._messages = self._build_initial_messages(task_prompt)
        self._iterations = 0

        final_answer = await self._invoke_loop()

        # If agent is waiting for user input, return immediately
        # Do NOT enter human feedback loop — the graph handles resumption
        if self._is_waiting_for_user(final_answer):
            return final_answer

        # Handle human feedback if enabled (developer/reviewer feedback, not user input)
        if self.ask_for_human_input:
            final_answer = await self._handle_human_feedback(final_answer)

        return final_answer

    async def _execute_tool(self, tool_call: dict[str, Any]) -> str:
        """Execute a single tool call.

        Args:
            tool_call: The tool call dict with name, args, and id.

        Returns:
            The tool execution result as a string.
        """
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        # Find the tool in our tools list
        tool_map = {t.name: t for t in self.tools}
        tool_fn = tool_map.get(tool_name)

        if not tool_fn:
            return f"Error: Tool '{tool_name}' not found. Available tools: {self.tools_names}"

        try:
            result = await tool_fn.ainvoke(tool_args)
            if self.tools_handler:
                self.tools_handler.last_used_tool = {
                    "name": tool_name,
                    "args": tool_args,
                    "result": result,
                }
            return str(result)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"


async def execute_task(
    agent: Any,
    description: str,
    tools: list[Any],
    expected_output: str | None = None,
    chat_history: list[dict] | None = None,
    context: str | None = None,
    output_json: type | None = None,
    output_pydantic: type | None = None,
    response_model: type | None = None,
    knowledge: Any | None = None,
    memory: Any | None = None,
    n_results: int = 5,
    max_iter: int = 25,
    use_system_prompt: bool = False,
    system_template: str | None = None,
    prompt_template: str | None = None,
    response_template: str | None = None,
    ask_for_human_input: bool = False,
    human_input_fn: Any | None = None,
    respect_context_window: bool = True,
    status_callback: Any | None = None,
) -> str:
    """Execute a task end-to-end: build prompt → create executor → invoke → return result.

    This is the top-level function that ties together all lib modules:
    1. prepare_task_prompt (task_prompt.py) — builds the task prompt with schema, context, knowledge
    2. build_execution_prompt (prompts.py) — builds system/role prompt + stop words
    3. AgentExecutor — runs the ReAct loop with tools and human feedback

    Mirrors CrewAI's Agent.execute_task() flow:
        _prepare_task_execution → handle_knowledge_retrieval → _finalize_task_prompt → executor.invoke

    Args:
        agent: Agent-like object with .role, .goal, .backstory attributes.
        description: The task description.
        tools: List of LangChain tools available to the agent.
        expected_output: Expected output criteria (optional).
        chat_history: Conversation history (optional).
        context: Context string (optional).
        output_json: Pydantic model for JSON output (optional).
        output_pydantic: Pydantic model for structured output (optional).
        response_model: If set, schema instructions skipped (optional).
        knowledge: Knowledge instance for retrieval (optional).
        n_results: Max knowledge results (default 5).
        max_iter: Max ReAct iterations (default 25).
        use_system_prompt: Whether to use system prompt mode.
        system_template: Custom system template.
        prompt_template: Custom prompt template.
        response_template: Custom response template.
        ask_for_human_input: Whether to enable human feedback loop.
        human_input_fn: Callable for collecting human feedback.
        respect_context_window: Whether to handle context overflow.

    Returns:
        The agent's final answer string.
    """
    from app.lib.prompts import build_execution_prompt
    from app.lib.task_prompt import prepare_task_prompt
    from app.lib.tool_schema import tools_to_prompt

    # 1. Build the task prompt (description + schema + context + memory + knowledge)
    task_prompt = await prepare_task_prompt(
        description=description,
        expected_output=expected_output,
        chat_history=chat_history,
        context=context,
        output_json=output_json,
        output_pydantic=output_pydantic,
        response_model=response_model,
        knowledge=knowledge,
        memory=memory,
        n_results=n_results,
    )

    # 2. Build execution prompt (role_playing + tools slices → system/user prompt)
    prompt_result, stop_words, rpm_limit_fn = build_execution_prompt(
        agent=agent,
        tools=tools,
        use_system_prompt=use_system_prompt,
        system_template=system_template,
        prompt_template=prompt_template,
        response_template=response_template,
    )

    # 3. Build tool names and descriptions
    tool_names = ", ".join(t.name for t in tools) if tools else ""
    tools_description = tools_to_prompt(tools) if tools else ""

    # 4. Get LLM
    from app.llm.client import get_client
    llm = get_client()

    # 5. Bind tools to LLM for native function calling
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    # 6. Create and invoke executor
    executor = AgentExecutor(
        llm=llm_with_tools,
        agent=agent,
        tools=tools,
        prompt=prompt_result,
        stop_words=stop_words,
        max_iter=max_iter,
        tools_names=tool_names,
        tools_description=tools_description,
        respect_context_window=respect_context_window,
        request_within_rpm_limit=rpm_limit_fn,
        response_model=response_model or output_pydantic or output_json,
        ask_for_human_input=ask_for_human_input,
        human_input_fn=human_input_fn,
        status_callback=status_callback,
    )

    return await executor.invoke(task_prompt)
