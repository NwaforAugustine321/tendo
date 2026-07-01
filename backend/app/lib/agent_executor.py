from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any
from pydantic import BaseModel, Field, PrivateAttr
from app.lib.i18n import _get_i18n
from app.lib.json_parser import parse_json_output
from app.lib.prompts import StandardPromptResult, SystemPromptResult
from langchain_core.callbacks import AsyncCallbackHandler

logger = logging.getLogger(__name__)


FINAL_ANSWER_OPEN = "<Final_Answer>"
FINAL_ANSWER_CLOSE = "</Final_Answer>"
ACTION_REGEX = re.compile(r"<Action>(.*?)</Action>", re.DOTALL)
ACTION_INPUT_REGEX = re.compile(r"<Action_Input>(.*?)(?:</Action_Input>|$)", re.DOTALL)

WAITING_USER_INPUT="awaiting_user_input"
WORKFLOW=['completed']
ROUTES_SUB_AGENT="__ROUTE__"


def _slice(key: str) -> str:
    """Get a raw prompt slice template from translations."""
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")



class ThinkingStreamCallback(AsyncCallbackHandler):
    """Streams thinking/thought to  via thinking_callback during agent execution."""

    def __init__(self, thinking_callback: Callable | None = None):
        super().__init__()
        self.thinking_callback = thinking_callback
        self._buffer = ""
        self._last_emitted_len = 0

    def reset(self) -> None:
        self._buffer = ""
        self._last_emitted_len = 0

    async def _send(self, msg: dict) -> None:
        if not self.thinking_callback:
            return
        try:
            await self.thinking_callback(msg)
        except Exception:
            pass

    async def on_llm_new_token(self, token: str, *, chunk=None, **kwargs: Any) -> None:
       
        if not token and not chunk:
            return
      
        if chunk and hasattr(chunk, 'additional_kwargs') and "reasoning_content" in chunk.additional_kwargs:
            reasoning = chunk.message.additional_kwargs.get("reasoning_content")
            if reasoning:
                await self._send({"type": "thought", "data": reasoning})
                return

        if not token:
            return

        self._buffer += token
        

        # Detect <Thought> and stream content progressively
        if "<Thought>" in self._buffer:
            after = self._buffer.split("<Thought>", 1)[1]
            # Remove closing tag if present
            thought_text = after.split("</Thought>", 1)[0].strip()
            # Strip any partial closing tag at the end (e.g. "</Thou", "</Thought")
            import re as _re
            thought_text = _re.sub(r"</T(?:h(?:o(?:u(?:g(?:h(?:t)?)?)?)?)?)?\s*$", "", thought_text).strip()
            if thought_text and len(thought_text) > self._last_emitted_len + 30:
                self._last_emitted_len = len(thought_text)
                await self._send({"type": "thought", "data": thought_text})

    async def on_llm_start(self, serialized: dict | None = None, prompts: list | None = None, **kwargs: Any) -> None:
        self.reset()

    async def on_chat_model_start(self, serialized: dict | None = None, messages: list | None = None, **kwargs: Any) -> None:
        self.reset()
        await self._send({"type": "thinking", "data": "Thinking..."})

    async def on_llm_end(self, response: Any = None, **kwargs: Any) -> None:
        pass



class AgentExecutor(BaseModel):
    """Agent Executor that drives the execution loop.

    Usage:
        executor = AgentExecutor(
            llm=llm,
            agent=agent,
            tools=parsed_tools,
            prompt=prompt,
            stop_words=stop_words,
            max_iter=25,
            tools_names=get_tool_names(parsed_tools),
            tools_description=render_text_description_and_args(parsed_tools),
            respect_context_window=True,
            request_within_rpm_limit=rpm_limit_fn,
            response_model=MyOutputModel,
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
    thinking_callback: Any | None = Field(
        default=None,
        description="Async callable for thinking status — renamed internally but kept for compat.",
    )

    # Internal state
    _messages: list[dict[str, Any]] = PrivateAttr(default_factory=list)
    _iterations: int = PrivateAttr(default=0)
    _tool_call_history: set = PrivateAttr(default_factory=set)

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
        if self.thinking_callback:
            try:
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(self.thinking_callback):
                    await self.thinking_callback(text)
                else:
                    await asyncio.to_thread(self.thinking_callback, text)
            except Exception:
                pass

    async def _emit_thinking(self, text: str) -> None:
        """Send text directly to thinking_callback if configured."""
        if not self.thinking_callback or not text:
            return
        try:
            import asyncio
            import inspect
            if inspect.iscoroutinefunction(self.thinking_callback):
                await self.thinking_callback(text)
            else:
                await asyncio.to_thread(self.thinking_callback, text)
        except Exception:
            pass

    @staticmethod
    def _parse_tool_input(raw_input: str) -> dict[str, Any]:
        """Parse tool input string into a dict. Handles truncated or messy JSON."""
        raw_input = raw_input.strip()

        # Try direct json.loads first
        try:
            result = json.loads(raw_input)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        # Find the JSON object from first { to last }
        start = raw_input.find("{")
        end = raw_input.rfind("}")
        if start != -1 and end > start:
            try:
                result = json.loads(raw_input[start:end + 1])
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass

        return None

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

    async def _invoke_loop(self) -> str:
        """Run the LLM invocation loop with dual-mode tool calling.

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

        
            try:
                response = await self.llm.ainvoke(self._messages)
                if response is None:
                        logger.warning("LLM stream returned no chunks")
                        self._messages.append({"role": "user", "content": "Please provide a response."})
                        continue
            except Exception as e:
                if is_context_length_exceeded(e):
                    await handle_context_length(
                        messages=self._messages,
                        respect_context_window=self.respect_context_window,
                    )
                    continue
                raise

            content = response.content
            if isinstance(content, list):
                content = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            raw = content.strip() if content else ""


            if not raw:
                logger.warning("LLM returned empty content — asking to retry")
                self._messages.append({"role": "user", "content": "Please provide a response."})
                continue


            # --- Mode 2: Native tool calls ---
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
                    # If delegation/coworker tool returns routing signal, return immediately
                    if ROUTES_SUB_AGENT in str(tool_result):
                        await self._emit_status("Checking information...")
                        return str(tool_result)
                    
                continue

           
            # --- Mode 2a: Check for XML <Action>/<Action_Input> tags ---
            action_name_match = ACTION_REGEX.search(raw)
            action_input_match = ACTION_INPUT_REGEX.search(raw)
            await self._emit_status("Checking information...")

            # If <Action> found but no <Action_Input>, ask LLM to complete
            if action_name_match and not action_input_match:
                self._messages.append({"role": "assistant", "content": raw})
                self._messages.append({
                    "role": "user",
                    "content": "You provided an <Action> but missing <Action_Input>. "
                               "Please provide the complete tool call with <Action_Input>{JSON}</Action_Input>."
                })
                continue

            if action_name_match and action_input_match:
                tool_name = action_name_match.group(1).strip()
                tool_input_raw = action_input_match.group(1).strip()
                tool_args = self._parse_tool_input(tool_input_raw)

                # If JSON parsing failed, ask LLM to retry with proper format
                if tool_args is None:
                    self._messages.append({"role": "assistant", "content": raw})
                    self._messages.append({
                        "role": "user",
                        "content": f"Error: Could not parse your <Action_Input> as valid JSON. "
                                   f"Please retry with valid JSON enclosed in <Action_Input>...</Action_Input> tags."
                    })
                    continue

                
                self._messages.append({"role": "assistant", "content": raw})
                tool_call = {"name": tool_name, "args": tool_args, "id": f"text_{tool_name}"}
                result_str = await self._execute_tool(tool_call)

                # If delegation/coworker tool returns routing signal, return immediately
                if ROUTES_SUB_AGENT in result_str:
                    await self._emit_status("Checking information...")
                    return result_str
               
                self._messages.append({"role": "user", "content": f"Observation: {result_str}"})
                continue

            # --- Mode 2b: Try to parse as structured JSON with tool_requests ---
          
            parsed_data = None
            try:
                parsed_data = parse_json_output(raw)
            except (json.JSONDecodeError, ValueError, TypeError):
                self._messages.append({"role": "assistant", "content": raw})
                self._messages.append({
                    "role": "user",
                    "content": "Error: Your response is not valid JSON. Please respond with a valid JSON object."
                })
                continue

            # If parsed JSON has workflow_state awaiting_user_input, return immediately
            await self._emit_status("Checking information...")
            if parsed_data and isinstance(parsed_data, dict):
                workflow_state = parsed_data.get("workflow_state", "")
                if str(workflow_state).lower() == WAITING_USER_INPUT:
                    response_text = parsed_data.get("response", "")
                    if response_text:
                        await self._emit_thinking(response_text)
                    return raw

            # If parsed JSON has tool_requests, execute them and continue
            if parsed_data and isinstance(parsed_data, dict):
                tool_requests = parsed_data.get("tool_requests")
                if tool_requests and isinstance(tool_requests, list) and len(tool_requests) > 0:
                    await self._emit_status("Checking information...")
                    # Send response text to thinking_callback
                    response_text = parsed_data.get("response", "")
                    if response_text:
                        await self._emit_thinking(response_text)
                    self._messages.append({"role": "assistant", "content": raw})

                    # Execute each tool request using _execute_tool
                    all_results = []
                    for tr in tool_requests:
                        tool_name = tr.get("tool", "")
                        tool_args = tr.get("arguments", tr.get("params", {}))
                        tool_call = {"name": tool_name, "args": tool_args, "id": f"text_{tool_name}"}
                        result_str = await self._execute_tool(tool_call)
                        logger.info(f"[Executor] Tool '{tool_name}' result: {result_str[:200]}")

                        # If delegation/coworker tool returns routing signal, return immediately
                        if ROUTES_SUB_AGENT in result_str:
                            await self._emit_status("Checking information...")
                            return result_str
                        

                        all_results.append(f"Tool '{tool_name}': {result_str[:500]}")

                    # Feed results back and continue loop for final answer
                    observation = "\n".join(all_results)
                    self._messages.append({"role": "user", "content": f"Observation: {observation}"})
                    continue

                # JSON response without tool_requests — return as final answer
                if self._is_waiting_for_user(raw):
                    return raw
                return raw

            # Non-JSON text response — return as final answer
            if self._is_waiting_for_user(raw):
                return raw
            return raw

        # Max iterations — force final answer
        force_msg = _slice("force_final_answer")
        self._messages.append({"role": "user", "content": force_msg})
        response = await self.llm.ainvoke(self._messages)
        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        raw = content.strip() if content else ""
        if FINAL_ANSWER_OPEN in raw:
            fa_match = re.search(r"<Final_Answer>(.*?)(?:</Final_Answer>|$)", raw, re.DOTALL)
            return fa_match.group(1).strip() if fa_match else raw.split(FINAL_ANSWER_OPEN, 1)[1].strip()
        return raw

    def _is_waiting_for_user(self, raw: str) -> bool:
        """Check if the agent output indicates it's waiting for user input.

        Detects either:
        - workflow_status "waiting_for_user" in JSON output

        Args:
            raw: The raw agent output string.

        Returns:
            True if the agent is waiting for user input.
        """

        try:
            data = parse_json_output(raw)
            return data.get("workflow_status") == "waiting_for_user"
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            return False

    async def invoke(self, task_prompt: str) -> str:
        """Execute the agent loop until a final answer is produced.

        Drives the loop:
        1. Send messages to LLM
        2. If LLM calls tools -> execute tools, append results, continue
        3. If LLM produces final answer -> return
        4. If workflow_status is "waiting_for_user" -> return immediately
        5. If max_iter reached -> force final answer

        Args:
            task_prompt: The fully assembled task prompt.

        Returns:
            The agent's final answer string.
        """
        self._messages = self._build_initial_messages(task_prompt)
        self._iterations = 0
        self._tool_call_history = set()

        final_answer = await self._invoke_loop()

        # If agent is waiting for user input, return immediately
        if self._is_waiting_for_user(final_answer):
            return final_answer

  
        if self.response_model and final_answer:
            final_answer = await self._validate_and_retry(final_answer)

        return final_answer

    async def _validate_and_retry(self, final_answer: str, max_retries: int = 2) -> str:
        """Validate final answer against response_model. Retry with error message if invalid."""
        from app.lib.i18n import _get_i18n

        for _ in range(max_retries):
            try:
                # Try to parse and validate against the Pydantic model
                clean = final_answer.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(clean) if clean.startswith("{") else None
                if data:
                    self.response_model(**data)
                # Validation passed
                return final_answer
            except Exception as e:
                error_str = str(e)
                logger.debug(f"[Executor] Validation failed: {error_str[:200]}")
                i18n = _get_i18n()
                validation_msg = i18n.get("errors.validation_error")
                if validation_msg:
                    retry_msg = validation_msg.format(
                        guardrail_result_error=error_str[:500],
                        task_output=final_answer[:500],
                    )
                    self._messages.append({"role": "assistant", "content": final_answer})
                    self._messages.append({"role": "user", "content": retry_msg})
                    final_answer = await self._invoke_loop()
                else:
                    break

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

        # --- Req 13: Detect repeated tool usage ---
        call_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True, default=str)}"
        if call_signature in self._tool_call_history:
            from app.lib.i18n import _get_i18n
            i18n = _get_i18n()
            repeated_msg = i18n.get("errors.task_repeated_usage")
            self._messages.append({"role": "user", "content": repeated_msg})
            return repeated_msg
        self._tool_call_history.add(call_signature)

        # Find the tool in our tools list
        tool_map = {t.name: t for t in self.tools}
        tool_fn = tool_map.get(tool_name)

        if not tool_fn:
            error_msg = f"Error: Tool '{tool_name}' not found. Available tools: {self.tools_names}"
            self._messages.append({"role": "user", "content": f"Observation: {error_msg}"})
            return error_msg

        try:
            result = await tool_fn.ainvoke(tool_args)
            if self.tools_handler:
                self.tools_handler.last_used_tool = {
                    "name": tool_name,
                    "args": tool_args,
                    "result": result,
                }
            result_str = str(result)
            self._messages.append({"role": "user", "content": f"Observation: {result_str}"})

   
            post_reasoning = _slice("post_tool_reasoning")
            if post_reasoning:
                self._messages.append({"role": "user", "content": post_reasoning})

            return result_str
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {e}"
            self._messages.append({"role": "user", "content": f"Observation: {error_msg}"})
            return error_msg


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
    respect_context_window: bool = True,
    thinking_callback: Any | None = None,
) -> str:
    """Execute a task end-to-end: build prompt → create executor → invoke → return result.

    Returns:
        The agent's final answer string.
    """
    from app.lib.prompts import build_execution_prompt
    from app.lib.task_prompt import prepare_task_prompt
    from app.lib.tool_schema import tools_to_prompt

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

    thinking_cb = None
    if thinking_callback:
        thinking_cb = ThinkingStreamCallback(thinking_callback=thinking_callback)
 

    from app.llm.client import get_client
    llm = get_client(callbacks=[thinking_cb] if thinking_cb else None)


    from app.config.settings import settings as _settings

    if tools and _settings.native_tool_calling:
        try:
            llm_with_tools = llm.bind_tools(tools)
        except (NotImplementedError, TypeError, AttributeError, Exception) as e:
            logger.info(f"Native tool binding failed ({e.__class__.__name__}), using text-based ReAct")
            llm_with_tools = llm
    else:
        llm_with_tools = llm

 
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
        thinking_callback=thinking_callback,
    )

    raw = await executor.invoke(task_prompt)

    # Strip internal reasoning XML tags before returning to caller
    from app.lib.text_utils import strip_internal_reasoning
    result = strip_internal_reasoning(raw)

    # Try to parse as JSON — if it fails and response_model is set, retry once
    # Skip retry if the output is a routing signal (e.g. __ROUTE__:transactions)
    if response_model or output_pydantic or output_json:
        if "__ROUTE__:" not in result:
            try:
                parse_json_output(result)
            except (json.JSONDecodeError, ValueError, TypeError):
                # JSON parse failed — ask LLM to fix the output
                logger.warning(f"[execute_task] JSON parse failed, retrying: {result[:100]}")
                fix_messages = [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": "Your response is not valid JSON. Please provide your answer as a valid JSON object matching the expected schema."},
                ]
                executor._messages.extend(fix_messages)
                retry_raw = await executor._invoke_loop()
                result = strip_internal_reasoning(retry_raw)

    # --- Req 11: Pre-review output improvement using accumulated lessons ---
    result = await _apply_pre_review(result)

    return result


async def _apply_pre_review(output: str) -> str:
    """Apply accumulated lessons to improve output before returning .

    Skips if no lessons exist or prompts are missing.
    """
    from app.lib.i18n import _get_i18n
    from app.memory.memory import get_memory

    i18n = _get_i18n()
    system_prompt = i18n.get("slices.hitl_pre_review_system")
    user_template = i18n.get("slices.hitl_pre_review_user")

    if not system_prompt or not user_template:
        return output

    try:
        # Retrieve stored lessons from /lessons scope
        memory = get_memory("/lessons")
        matches = await memory.recall("output improvement lessons", limit=5)

        if not matches:
            return output

        lessons_text = "\n".join(f"- {m.record.content}" for m in matches)

        from app.llm.client import get_client
        llm = get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_template.format(output=output, lessons=lessons_text)},
        ]
        response = await llm.ainvoke(messages)
        improved = response.content.strip() if response.content else ""

        return improved if improved else output
    except Exception as e:
        logger.debug(f"Pre-review failed, using original output: {e}")
        return output


async def distill_lessons(method_name: str, output: str, feedback: str) -> list[str]:
    """Extract generalizable lessons from human feedback .

    Args:
        method_name: The method/agent that produced the output.
        output: The original agent output.
        feedback: The human feedback on that output.

    Returns:
        List of extracted lesson strings (empty if none).
    """
    from app.lib.i18n import _get_i18n
    from app.memory.memory import get_memory

    i18n = _get_i18n()
    system_prompt = i18n.get("slices.hitl_distill_system")
    user_template = i18n.get("slices.hitl_distill_user")

    if not system_prompt or not user_template:
        return []

    try:
        import json
        from app.llm.client import get_client
        llm = get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_template.format(
                method_name=method_name,
                output=output,
                feedback=feedback,
            )},
        ]
        response = await llm.ainvoke(messages)
        raw = response.content.strip() if response.content else ""

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        lessons = json.loads(raw) if raw.startswith("[") else []

        if lessons:
            memory = get_memory("/lessons")
            await memory.remember_many(lessons, source="hitl_distillation")

        return lessons
    except Exception as e:
        logger.debug(f"Lesson distillation failed: {e}")
        return []
