from __future__ import annotations
import json
import logging
import re
import time
from app.lib.tool_schema import tools_schema_and_description
from typing import Any, TYPE_CHECKING
from app.llm.client import get_client
from app.lib.text_utils import strip_internal_reasoning
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage as LCAIMessage
from app.lib.context_handler import handle_context_length, is_context_length_exceeded
from app.lib.i18n import _get_i18n
from app.lib.json_parser import parse_json_output
from app.runtime.tool_binder import ToolBinder
from app.lib.prompts import prepare_system_prompt, prepare_planner_task_prompt, format_conversation
from app.lib.prompts import prepare_task_prompt


if TYPE_CHECKING:
    from app.agents.models import DomainAgentProtocol

i18n = _get_i18n()

logger = logging.getLogger(__name__)

FINAL_ANSWER_REGEX = re.compile(
    r"<Final_Answer>(.*?)(?:</Final_Answer>|$)", re.DOTALL)
ACTION_REGEX = re.compile(r"<Action>(.*?)(?:</Action>|$)", re.DOTALL)
ACTION_INPUT_REGEX = re.compile(
    r"<Action_Input>(.*?)(?:</Action_Input>|$)", re.DOTALL)
WAITING_USER_INPUT_REGEX = re.compile(
    r"<Waiting_User_Input>(.*?)(?:</Waiting_User_Input>|$)", re.DOTALL)
THOUGHT_REGEX = re.compile(r"<Thought>(.*?)(?:</Thought>|$)", re.DOTALL)
Update_Status_REGEX = re.compile(
    r"<Stream_Update>(.*?)(?:</Stream_Update>|$)", re.DOTALL)


class AgentRuntime:

    def __init__(
        self,
        tool_binder: ToolBinder,
        llm: Any = None,
        agent: Any = None,
        context: str = '',
        tools: list = [],
        expected_output: str | None = None,
        reflection_stage: Any | None = None,
        conversation_messages: list[dict[str, Any]] | None = [],
        max_iter: int = 10,
        max_validation_retries: int = 5,
        output_pydantic: type | None = None,
        output_json: type | None = None,
        guardrail_llm: Any | None = None,
        allowed_input_guardrail: bool = False,
        allowed_output_guardrail: bool = False,
        allowed_retrieval_guardrail: bool = False,
        allowed_tool_guardrail: bool = False,
        allowed_dialog_guardrail: bool = False,
        use_system_prompt: bool = False,
        system_prompt: str = '',
        max_token: int | None = None,
        max_thinking_steps: int = 5
    ) -> None:
        self._llm = llm
        self._context = context
        self._tools = tools
        self._tool_binder = tool_binder
        self._agent = agent
        self._conversation_messages: list[dict[str,
                                               Any]] | None = conversation_messages or []
        self._expected_output = expected_output
        self._reflection_stage = reflection_stage
        self._max_iter = max_iter
        self._max_validation_retries = max_validation_retries
        self._messages: list[dict[str, Any]] = []
        self._iterations: int = 0
        self._tool_call_history: set[str] = set()
        self._tools_names: str = ""
        self._tools_description: str = ""
        self._output_pydantic: type | None = output_pydantic
        self._output_json: type | None = output_json
        self._bound_tools: list[Any] = []
        self._guardrail_llm = guardrail_llm
        self._allowed_input_guardrail = allowed_input_guardrail
        self._allowed_output_guardrail = allowed_output_guardrail
        self._allowed_tool_guardrail = allowed_tool_guardrail
        self._allowed_dialog_guardrail = allowed_dialog_guardrail
        self._allowed_retrieval_guardrail = allowed_retrieval_guardrail
        self._rail_options: dict = {}
        self._use_system_prompt = use_system_prompt
        self._system_prompt = system_prompt
        self._chat_history: list[Any] = []
        self._last_final_answer: str | None = None
        self._guardrail = None
        self._task_msg_check: str = ''
        self._max_token = max_token
        self._max_thinking_steps = max_thinking_steps

        if self._use_system_prompt and not self._system_prompt:
            raise "System prompt is enable and it require system prompt param"

        if self._llm == None:
            self._llm = get_client(config={
                "max_token": max_token
            })

    def bind_tool(self, tools: list[Any] = []):
        _tools: list[Any] = []

        if len(tools) > 0:
            _tools.extend(tools)
        if len(self._tools) > 0:
            _tools.extend(self._tools)

        self._tools = _tools

    async def execute(self, task,  context: str = '', task_msg_check: str = '', chat_history: list[Any] = [], use_plan_mode: bool = False, messages: list[Any] | None = None) -> Execution:
        agent = self._agent
        start = time.perf_counter()
        self._chat_history = chat_history

        self._iterations = 0
        self._messages = []
        self._tool_call_history = set()
        self._context += context

        if messages:
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    self._messages.append(
                        {"role": "user", "content": msg.content})
                elif isinstance(msg, LCAIMessage):
                    self._messages.append(
                        {"role": "assistant", "content": msg.content})

        if self._allowed_input_guardrail:
            safety_check = await self._guardrail.check_content_safety(
                [{"role": "user", "content":  task}]
            )

            if not safety_check.allowed:
                return safety_check.response or "Request blocked by safety check."

        if hasattr(self._llm, 'bind_tools') and self._tools:
            self._llm = self._llm.bind_tools(self._tools)

        if self._use_system_prompt is not True:
            #   prompt_tools = [] if (hasattr(self._llm, 'bind_tools') and self._tools) else self._tools
            prompt, _ = await prepare_system_prompt(
                agent=self._agent,
                tools=self._tools,
                max_thinking_steps=self._max_thinking_steps
            )

            self._system_prompt = prompt + self._system_prompt

        if use_plan_mode:
            task_prompt = await prepare_planner_task_prompt(
                description=task,
                output_pydantic=self._output_pydantic
            )
        else:
            task_prompt = await prepare_task_prompt(
                description=task,
                expected_output=self._expected_output,
                output_pydantic=self._output_pydantic,
                output_json=self._output_json,
                context=self._context,
                # chat_history=chat_history

            )

        self._task_prompt = task_prompt

        self._prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder("chat_history", optional=True),
            MessagesPlaceholder("history", optional=True),
            ("user", "{user_message}"),
        ])

        try:

            raw = await self._invoke_loop()

        except Exception as e:
            logger.error("Execution failed: %s", e)
            await self._tool_binder.release()
            return "I'm temporarily unable to process this request. Please try again shortly."

        await self._tool_binder.release()
        return strip_internal_reasoning(raw) if raw else ""

    @staticmethod
    def _parse_tool_input(raw_input: str) -> dict[str, Any] | None:
        try:
            result = parse_json_output(raw_input)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return None

    async def _execute_tool(self, tool_call: dict[str, Any]) -> str:
        tool_name = tool_call.get("name", "").strip()
        tool_args = tool_call.get("args", {})

        if isinstance(tool_args, dict):
            tool_args = {k.strip(): v for k, v in tool_args.items()}
        call_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True, default=str)}"
        # if call_signature in self._tool_call_history:

        #     repeated_msg = i18n.get("errors.task_repeated_usage")
        #     self._messages.append({"role": "user", "content": repeated_msg})
        #     return repeated_msg
        self._tool_call_history.add(call_signature)
        tool_map = {t.name: t for t in self._tools}
        tool_fn = tool_map.get(tool_name)

        if not tool_fn:
            observation = i18n.get("errors.wrong_tool_name").replace(
                "{tool}", tool_name).replace("{tools}", tools_schema_and_description(self._tools))
            return observation
        r = await self._run_tool_fn(tool_name, tool_args, tool_fn)

        return r

    async def _run_tool_fn(self, tool_name: str, tool_args: dict, tool_fn: Any) -> str:

        try:

            tool_result = await tool_fn.ainvoke(tool_args)

            observation = i18n.get("slices.post_tool_reasoning")
            observation += f"{tool_result}\n\n"

            return observation
        except Exception as e:

            logger.warning(f"Tool '{tool_name}' failed: {e}")
            error_msg = "{tool_name} tool failed"
            observation = i18n.get("slices.post_tool_reasoning")
            observation += f"\n\n{error_msg}\n\n"
            return observation

    async def _validate_and_retry(self, final_answer: str, output_pydantic: type | None = None, output_json: type | None = None) -> str | None:

        validation_model = output_pydantic or output_json
        if not validation_model:
            return final_answer
        for _ in range(self._max_validation_retries):
            try:
                data = parse_json_output(final_answer)
                if data:
                    validation_model(**data)
                return final_answer
            except Exception as e:
                error_str = str(e)
                validation_msg = i18n.get("errors.validation_error")
                retry_msg = validation_msg.format(
                    guardrail_result_error=error_str[:500], task_output=final_answer[:500])
                self._messages.append(
                    {"role": "assistant", "content": final_answer})
                self._messages.append({"role": "user", "content": retry_msg})
                return None

        return final_answer

    async def _invoke_loop(self) -> str:
        first_call = True
        while True:
            print(self._agent.name)

            self._iterations += 1
            if self._iterations > self._max_iter:
                await self._force_final_answer()

            if first_call:
                user_msg = self._task_prompt
                first_call = False
            else:
                user_msg = ""

            response = await self._invoke_llm_safe(user_msg)

            print(response)
            print(response.tool_calls)

            if response.tool_calls and len(response.tool_calls) > 0:
                result = await self._handle_native_tool_calls(response)
                continue

            if response is None or not response.content:
                self._handle_empty_response()
                continue

            content = response.content
            if isinstance(content, list):
                content = "".join(block.get("text", "") if isinstance(
                    block, dict) else str(block) for block in content)
            raw = content.strip() if content else ""

            if not raw:
                self._handle_empty_response()
                continue

            valid_raw_response = await self._validate_and_retry(
                raw,
                output_pydantic=self._output_pydantic,
                output_json=self._output_json,
            )

            if valid_raw_response is None:
                continue

            result = await self._handle_text_response(valid_raw_response)
            if result is None:
                continue

            return result

    async def _invoke_llm_safe(self, user_message: str = "") -> Any:
        try:
            chain = self._prompt_template | self._llm

            response = await chain.ainvoke({
                "system_prompt": self._system_prompt,
                "history": self._messages,
                "user_message": user_message,
                "chat_history": self._chat_history
            })
            return response

        except Exception as e:
            if is_context_length_exceeded(e):
                self._messages = await handle_context_length(messages=self._messages, respect_context_window=True)
                return None
            # Handle rate limit (429) and other transient API errors gracefully
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "limit" in error_str.lower():
                logger.warning(f"LLM rate limit hit: {error_str[:200]}")
                raise RuntimeError(
                    f"LLM rate limit exceeded: {error_str[:200]}")
            raise

    def _handle_empty_response(self) -> bool:
        empty_msg = i18n.get("slices.empty_response")
        self._messages.append({"role": "user", "content": empty_msg})

    async def _handle_native_tool_calls(self, response: Any) -> str | None:
        self._messages.append(
            {"role": "assistant", "content": response.content or "", "tool_calls": response.tool_calls})
        for tc in response.tool_calls:
            tool_result = await self._execute_tool(tc)
            print(
                f"[tool_call] {tc['name']} -> result: {str(tool_result)[:500]}")
            self._messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": str(tool_result)})
        return None

    async def _handle_text_response(self, raw: str) -> str | None:
        thought_match = THOUGHT_REGEX.search(raw)
        fa_match = FINAL_ANSWER_REGEX.search(raw)
        action_match = ACTION_REGEX.search(raw)
        input_match = ACTION_INPUT_REGEX.search(raw)

        if not thought_match and not fa_match and not action_match:
            return raw

        # Track last final answer seen so far
        if fa_match and fa_match.group(1).strip():
            self._last_final_answer = fa_match.group(1).strip()

        # <Thought> + <Final_Answer> → append message and continue (let the loop accumulate reasoning)
        if thought_match and fa_match:
            self._messages.append({"role": "assistant", "content": raw})
            content = fa_match.group(1).strip()
            if content:
                self._last_final_answer = content
            return None

        # <Thought> + <Action> → skip append, execute action directly
        if thought_match and action_match:

            if not input_match:
                force_tool_input_msg = i18n.get("errors.tool_arguments_error")
                self._messages.append({"role": "assistant", "content": raw})
                self._messages.append(
                    {"role": "user", "content": force_tool_input_msg})
                return None
            return await self._handle_xml_action(raw, action_match, input_match)

        # <Final_Answer> alone
        if fa_match:
            content = fa_match.group(1).strip()
            if not content:
                force_msg = i18n.get("errors.force_final_answer")
                force_msg += i18n.get("errors.force_final_answer_error")
                self._messages.append({"role": "assistant", "content": raw})
                self._messages.append({"role": "user", "content": force_msg})
                return None
            return content

        # <Action> alone
        if action_match and not input_match:
            force_tool_input_msg = i18n.get("errors.tool_action_error")
            self._messages.append({"role": "assistant", "content": raw})
            self._messages.append(
                {"role": "user", "content": force_tool_input_msg})
            return None
        if action_match and input_match:
            return await self._handle_xml_action(raw, action_match, input_match)

        # <Thought> alone → append message, continue loop
        if thought_match:
            self._messages.append({"role": "assistant", "content": raw})
            return None

        return None

    async def _handle_xml_action(self, raw: str, action_match: re.Match, input_match: re.Match) -> str | None:
        tool_name = action_match.group(1).strip()
        tool_args = self._parse_tool_input(input_match.group(1).strip())

        if tool_args is None:
            force_tool_input_msg = i18n.get("errors.tool_arguments_error")
            self._messages.append({"role": "assistant", "content": raw})
            self._messages.append(
                {"role": "user", "content": force_tool_input_msg})
            return None

        tool_id = f"text_{tool_name}"
        formatted_tool_calls = [
            {"id": tool_id, "type": "function", "function": {
                "name": tool_name, "arguments": json.dumps(tool_args)}}
        ]
        self._messages.append(
            {"role": "assistant", "content": "", "tool_calls": formatted_tool_calls})
        tool_call = {"name": tool_name, "args": tool_args, "id": tool_id}
        tool_result = await self._execute_tool(tool_call)

        self._messages.append(
            {"role": "tool", "tool_call_id": tool_id, "content": str(tool_result)})
        return None

    async def _force_final_answer(self):

        force_msg = i18n.get("errors.force_final_answer")
        force_msg += i18n.get("errors.force_final_answer_error")
        force_msg.replace("{formatted_answer}", str(self._last_final_answer))
        self._messages.append({"role": "user", "content": force_msg})
