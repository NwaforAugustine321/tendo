from __future__ import annotations
import asyncio
import inspect
import json
import logging
import re
import time
from app.lib.tool_schema import tools_schema_and_description
from app.runtime.tool_result import ToolResult
from typing import Any, TYPE_CHECKING
from app.llm.client import get_client
from app.execution.models import (
    Execution,
    Result,
    ExecutionMetrics,
    ReflectionOutput,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.lib.context_handler import handle_context_length, is_context_length_exceeded
from app.lib.i18n import _get_i18n
from app.lib.json_parser import parse_json_output
from app.lib.tool_schema import tools_schema_and_description
from app.runtime.tool_binder import ToolBinder
from app.lib.prompts import prepare_system_prompt,prepare_planner_task_prompt,format_conversation
from app.lib.prompts import prepare_task_prompt
from langchain_core.runnables import RunnableLambda, RunnableConfig
from app.guardrails.manager import GuardrailManager

guardrail = GuardrailManager()

if TYPE_CHECKING:
    from app.agents.models import DomainAgentProtocol

i18n = _get_i18n()

logger = logging.getLogger(__name__)

FINAL_ANSWER_REGEX = re.compile(r"<Final_Answer>(.*?)(?:</Final_Answer>|$)", re.DOTALL)
ACTION_REGEX = re.compile(r"<Action>(.*?)(?:</Action>|$)", re.DOTALL)
ACTION_INPUT_REGEX = re.compile(r"<Action_Input>(.*?)(?:</Action_Input>|$)", re.DOTALL)
WAITING_USER_INPUT_REGEX = re.compile(r"<Waiting_User_Input>(.*?)(?:</Waiting_User_Input>|$)", re.DOTALL)
THOUGHT_REGEX = re.compile(r"<Thought>(.*?)(?:</Thought>|$)", re.DOTALL)



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
        conversation_messages:list[dict[str, Any]] | None  = [],
        max_iter: int = 10,
        max_validation_retries: int = 5,
        thinking_callback: Any | None = None,
        output_pydantic: type | None = None,
        output_json: type | None = None,
        guardrail_llm: Any | None = None,
        allowed_input_guardrail: bool = False,
        allowed_output_guardrail: bool = False,
        allowed_retrieval_guardrail: bool = False,
        allowed_tool_guardrail: bool = False,
        allowed_dialog_guardrail: bool = False,
        use_system_prompt: bool = False,
        system_prompt : str  = '',
        max_token:int | None = None,
        max_thinking_steps: int = 5
    ) -> None:
        self._llm = llm
        self._context = context
        self._tools = tools
        self._tool_binder = tool_binder
        self._agent = agent
        self._conversation_messages:list[dict[str, Any]] | None =  conversation_messages or []
        self._expected_output = expected_output
        self._reflection_stage = reflection_stage
        self._max_iter = max_iter
        self._max_validation_retries = max_validation_retries
        self._thinking_callback = thinking_callback
        self._messages: list[dict[str, Any]] = []
        self._iterations: int = 0
        self._tool_call_history: set[str] = set()
        self._tools: list[Any] = []
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
        self._system_prompt  = system_prompt
        self._chat_history: list[Any] = []
        self._last_final_answer: str | None = None
        self._guardrail = guardrail
        self._task_msg_check: str = ''
        self._max_token = max_token
        self._max_thinking_steps = max_thinking_steps
        
        if self._use_system_prompt and not self._system_prompt:
          raise "System prompt is enable and it require system prompt param"

        if self._llm == None:
            self._llm = get_client(config={
                "max_token":max_token
            })

        
    def bind_tool(self,tools: list[Any] = []):
        _tools: list[Any] = []

        if len(tools) > 0:
            _tools.extend(tools)
        if len(self._tools) > 0:
            _tools.extend(self._tools)

        self._tools = _tools

        if self._tool_binder and len(_tools) > 0:
            self._bound_tools = self._tool_binder.bind(_tools)
            self._tools_names = ", ".join(getattr(t, "name", str(t)) for t in _tools)
            self._tools_description = tools_schema_and_description(_tools) if _tools else ""

        if  hasattr(self._llm, 'bind_tools'):
            self._llm = self._llm.bind_tools(self._tools)  
          
        
    async def execute(self,task,  context:str = '', task_msg_check: str = '', chat_history:list[Any] = [], use_plan_mode:bool = False) -> Execution:
        agent = self._agent
        start = time.perf_counter()
        self._chat_history = chat_history

        self._iterations = 0
        self._messages = []
        self._tool_call_history = set()
        self._context += context


        if self._allowed_input_guardrail:
            safety_check = await self._guardrail.check_content_safety(
               [{"role":"user", "content":  task}]
            )

            if not safety_check.allowed:
               elapsed_ms = (time.perf_counter() - start) * 1000
               return Execution(
                       result=Result(
                       status="failed",
                       response=safety_check.response,
                       ),
                       metrics=ExecutionMetrics(
                       iterations=self._iterations,
                       duration_ms=elapsed_ms,
                       tools_invoked=[],
                       ),
                       error=f"Failed: {safety_check.response}",
               )

        if hasattr(self._llm, 'bind_tools'):
            self._llm = self._llm.bind_tools(self._tools)  

        if self._use_system_prompt is not True:
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
            MessagesPlaceholder("chat_history",optional=True), 
            MessagesPlaceholder("history",optional=True),
            ("user", "{user_message}"),
        ])

        try:
           
             
            raw = await self._invoke_loop()   
            result = Result(
                  status="success",
                  response=raw,
            )

        except Exception as e:
            logger.error("Execution failed: %s", e)
            elapsed_ms = (time.perf_counter() - start) * 1000
            await self._tool_binder.release()
            # Return a structured JSON error response so callers parsing JSON don't crash
            error_response = json.dumps({
                "error": True,
                "message": str(e),
                "conversation_response": "I'm temporarily unable to process this request. Please try again shortly.",
                "is_task_trigger": False,
                "agent_selection": None,
                "shared_constraints": "",
            })
            return Execution(
                result=Result(status="failure", response=error_response),
                metrics=ExecutionMetrics(
                    iterations=self._iterations,
                    duration_ms=elapsed_ms,
                    tools_invoked=[],
                ),
                error=f"Failed: {e}",
            )

        reflection = ReflectionOutput()
        if self._reflection_stage is not None:
            try:
                reflection = await self._reflection_stage.reflect(
                    messages=self._messages,
                    tools_used=[getattr(t, "name", str(t)) for t in self._bound_tools],
                    iterations=self._iterations,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    domain_output=result.response,
                )
            except Exception as e:
                logger.warning("Reflection failed: %s", e)
                reflection = ReflectionOutput()

        elapsed_ms = (time.perf_counter() - start) * 1000
        tools_invoked = [
            {"name": getattr(t, "name", str(t)), "count": 1} for t in self._bound_tools
        ]
        metrics = ExecutionMetrics(
            iterations=self._iterations,
            duration_ms=elapsed_ms,
            tools_invoked=tools_invoked,
        )

        await self._tool_binder.release()

        return Execution(
            result=result,
            reflection=reflection,
            metrics=metrics,
        )


    async def _emit_status(self, text: str) -> None:
        if not self._thinking_callback:
            return
        try:
            if inspect.iscoroutinefunction(self._thinking_callback):
                await self._thinking_callback(text)
            else:
                await asyncio.to_thread(self._thinking_callback, text)
        except Exception:
            pass

    async def _emit_thinking(self, text: str) -> None:
        if not self._thinking_callback or not text:
            return
        try:
            if inspect.iscoroutinefunction(self._thinking_callback):
                await self._thinking_callback(text)
            else:
                await asyncio.to_thread(self._thinking_callback, text)
        except Exception:
            pass

    def _build_agent_system_prompt(self, domain_agent: Any = None) -> str:
        from app.lib.prompts import prepare_system_prompt

        # domain_agent should already have goal, role, backstory pre-loaded
        prompt_result, _ = prepare_system_prompt(
            agent=domain_agent,
            tools=self._tools,
            use_system_prompt=True,
        )

        if hasattr(prompt_result, 'system') and prompt_result.system:
            return prompt_result.system
        return prompt_result.prompt

    @staticmethod
    def _parse_tool_input(raw_input: str) -> dict[str, Any] | None:
        try:
            result = parse_json_output(raw_input)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return None

    def _is_waiting_for_user(self, raw: str) -> bool:
        """Check if the agent output indicates it's waiting for user input."""
        return bool(WAITING_USER_INPUT_REGEX.search(raw))


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
            observation = i18n.get("errors.wrong_tool_name").replace("{tool}",tool_name).replace("{tools}",tools_schema_and_description(self._tools))
            self._messages.append({"role": "user", "content":observation})
            return error_msg
        r = await self._run_tool_fn(tool_name, tool_args, tool_fn)
        return r

    async def _run_tool_fn(self, tool_name: str, tool_args: dict, tool_fn: Any) -> str:
        

        try:
            result = await tool_fn.ainvoke(tool_args)

            if isinstance(result, dict) and "content" in result:
                tool_result = ToolResult(**result)
            elif isinstance(result, ToolResult):
                tool_result = result
            else:
                tool_result = ToolResult(content=str(result))

            message_parts: list[dict] = []

            text_content = tool_result.content
            if tool_result.metadata:
                text_content += f"\n {json.dumps(tool_result.metadata, default=str)}"

            observation = i18n.get("slices.post_tool_reasoning")
            observation += f"{text_content}\n\n"
            message_parts.append({"type": "text", "text": observation})

            for img in tool_result.images:
                if img.startswith("data:") or img.startswith("http"):
                    message_parts.append({"type": "image_url", "image_url": {"url": img}})
                else:
                    message_parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})

            # Append as multimodal message if images present, otherwise plain text
            if tool_result.images:
                self._messages.append({"role": "user", "content": message_parts})
            else:
                observation = i18n.get("slices.post_tool_reasoning")
                observation += f"{text_content}\n\n"
                self._messages.append({"role": "user", "content":observation})

            return text_content
        except Exception as e:
            logger.warning(f"Tool '{tool_name}' failed: {e}")
            error_msg = "No results."
            observation = i18n.get("slices.post_tool_reasoning")
            observation += f"{error_msg}\n\n"

            self._messages.append({"role": "user", "content": observation})
            return error_msg


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
                retry_msg = validation_msg.format(guardrail_result_error=error_str[:500], task_output=final_answer[:500])
                self._messages.append({"role": "assistant", "content": final_answer})
                self._messages.append({"role": "user", "content": retry_msg})
                return None

        return final_answer

    async def _invoke_loop(self) -> str:
        while True:
            print(self._agent.name)
                
            self._iterations += 1
            if self._iterations > self._max_iter:
                await self._force_final_answer()

            response = await self._invoke_llm_safe()

            if response is None:
                self._handle_empty_response()
                continue

            # print(response)
            # print('\n\n\n')

            if response.tool_calls and len(response.tool_calls) > 0:
                result = await self._handle_native_tool_calls(response)
                continue

            content = response.content
            if isinstance(content, list):
                content = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)
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

    async def _invoke_llm_safe(self) -> Any:
        try:
            chain = self._prompt_template | self._llm
        
            response = await chain.ainvoke({
                "system_prompt": self._system_prompt,
                "history": self._messages,
                "user_message": self._task_prompt,
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
                raise RuntimeError(f"LLM rate limit exceeded: {error_str[:200]}")
            raise

    def _handle_empty_response(self) -> bool:
        empty_msg = i18n.get("slices.empty_response")
        self._messages.append({"role": "user", "content": empty_msg})
        

    async def _handle_native_tool_calls(self, response: Any) -> str | None:
        self._messages.append({"role": "assistant", "content": response.content or "", "tool_calls": response.tool_calls})
        for tc in response.tool_calls:
            tool_result = await self._execute_tool(tc)
            self._messages.append({"role": "tool", "tool_call_id": tc["id"], "content": str(tool_result)})
        return None


    async def _handle_text_response(self, raw: str) -> str | None:
        thought_match = THOUGHT_REGEX.search(raw)
        fa_match = FINAL_ANSWER_REGEX.search(raw)
        action_match = ACTION_REGEX.search(raw)
        input_match = ACTION_INPUT_REGEX.search(raw)

        # Track last final answer seen so far
        if fa_match and fa_match.group(1).strip():
            self._last_final_answer = fa_match.group(1).strip()

        # <Thought> + <Final_Answer> → only append thought, continue loop (don't return final answer)
        if thought_match and fa_match:
            self._messages.append({"role": "assistant", "content": raw})
            return None

        # <Thought> + <Action> → skip append, execute action directly
        if thought_match and action_match:
          
            if not input_match:
                force_tool_input_msg = i18n.get("errors.tool_arguments_error")
                self._messages.append({"role": "assistant", "content": raw})
                self._messages.append({"role": "user", "content": force_tool_input_msg})
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
            self._messages.append({"role": "user", "content": force_tool_input_msg})
            return None
        if action_match and input_match:
            return await self._handle_xml_action(raw, action_match, input_match)

        # <Thought> alone → append message, continue loop
        if thought_match:
            self._messages.append({"role": "assistant", "content": raw})
            return None

        return await self._handle_json_or_final(raw)

    async def _handle_xml_action(self, raw: str, action_match: re.Match, input_match: re.Match) -> str | None:
        tool_name = action_match.group(1).strip()
        tool_args = self._parse_tool_input(input_match.group(1).strip())
        if tool_args is None:
            force_tool_input_msg = i18n.get("errors.tool_arguments_error")
            self._messages.append({"role": "assistant", "content": raw})
            self._messages.append({"role": "user", "content": force_tool_input_msg})
            return None
        self._messages.append({"role": "assistant", "content": raw})
        tool_call = {"name": tool_name, "args": tool_args, "id": f"text_{tool_name}"}
        result_str = await self._execute_tool(tool_call)
        observation = i18n.get("slices.post_tool_reasoning")
        observation += f"{result_str}\n\n"
        self._messages.append({"role": "user", "content": observation})
        return None

    async def _handle_json_or_final(self, raw: str) -> str | None:
        parsed_data = None
        try:
            parsed_data = parse_json_output(raw)
        except (json.JSONDecodeError, ValueError, TypeError):
            if self._output_pydantic or self._output_json:
                self._messages.append({"role": "assistant", "content": raw})
                self._messages.append({"role": "user", "content": "Error: Your response is not valid JSON. Please respond with a valid JSON object."})
                return None
            self._messages.append({"role": "assistant", "content": raw})
            return None
        await self._emit_status("Checking information...")
        if parsed_data and isinstance(parsed_data, dict):
            if self._is_waiting_for_user(raw):
                response_text = parsed_data.get("response", "")
                if response_text:
                    await self._emit_thinking(response_text)
                return raw
            tool_requests = parsed_data.get("tool_requests")
            if tool_requests and isinstance(tool_requests, list) and len(tool_requests) > 0:
                return await self._handle_json_tool_requests(raw, parsed_data, tool_requests)
            # Detect raw tool call attempts — only when no output model expects JSON
            if not (self._output_pydantic or self._output_json):
                if parsed_data.get("tool") and parsed_data.get("arguments") is not None:
                    self._messages.append({"role": "assistant", "content": raw})
                    self._messages.append({"role": "user", "content": "You do not have access to that tool. Answer the user's question using only the information you already have. If you don't have the information, say so clearly."})
                    return None
                # Detect raw data dumps (not a proper response to the user)
                if not parsed_data.get("response") and not self._is_waiting_for_user(raw) and len(parsed_data) > 1:
                    self._messages.append({"role": "assistant", "content": raw})
                    self._messages.append({"role": "user", "content": "Do not return raw JSON data to the user. Summarize this information in a clear, natural response that directly answers the user's question."})
                    return None
            self._messages.append({"role": "assistant", "content": raw})
            self._messages.append({"role": "user", "content": "Please wrap your final response in <Final_Answer></Final_Answer> tags."})
            return None
        self._messages.append({"role": "assistant", "content": raw})
        self._messages.append({"role": "user", "content": "Please wrap your final response in <Final_Answer></Final_Answer> tags."})
        return None

    async def _handle_json_tool_requests(self, raw: str, parsed_data: dict, tool_requests: list) -> str | None:
        """Execute tool_requests from JSON response."""
        await self._emit_status("Checking information...")
        response_text = parsed_data.get("response", "")
        if response_text:
            await self._emit_thinking(response_text)
        self._messages.append({"role": "assistant", "content": raw})
        all_results = []
        for tr in tool_requests:
            tool_name = tr.get("tool", "")
            tool_args = tr.get("arguments", tr.get("params", {}))
            tool_call = {"name": tool_name, "args": tool_args, "id": f"text_{tool_name}"}
            result_str = await self._execute_tool(tool_call)
            logger.info(f"[Runtime] Tool '{tool_name}' result: {result_str[:200]}")
            all_results.append(f"Tool '{tool_name}': {result_str[:500]}")
        self._messages.append({"role": "user", "content": f"Observation: {chr(10).join(all_results)}"})
        return None

    def _extract_final_answer(self, raw: str) -> str:
        """Extract final answer from text, handling <Final_Answer> tags."""
        fa_match = FINAL_ANSWER_REGEX.search(raw)
        if fa_match:
            return fa_match.group(1).strip()
        return raw

    async def _force_final_answer(self):
    
        force_msg = i18n.get("errors.force_final_answer")
        force_msg += i18n.get("errors.force_final_answer_error")
        force_msg.replace("{formatted_answer}", str(self._last_final_answer))
        self._messages.append({"role": "user", "content": force_msg})
        # chain = self._prompt_template |  self._llm
        # response = await chain.ainvoke({
        #     "system_prompt": self._system_prompt,
        #     "history": self._messages,
        #     "user_message": self._task_prompt,
        #     "chat_history": self._chat_history
        # })
        # content = response.content
        # if isinstance(content, list):
        #     content = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)
        # raw = content.strip() if content else ""
        # fa_match = FINAL_ANSWER_REGEX.search(raw)
        # if fa_match:
        #     return fa_match.group(1).strip()
        # return "Could you please rephrase your request."
