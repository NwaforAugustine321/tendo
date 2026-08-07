
from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING
from app.lib.i18n import _get_i18n
from app.lib.pydantic_schema_utils import generate_model_description
from app.memory.memory import Memory
from typing import Iterable, Mapping, Any
from collections.abc import Callable
from typing import Any, Literal
from pydantic import BaseModel, Field
from app.lib.i18n import _get_i18n
from app.lib.tool_schema import tools_schema_and_description

logger = logging.getLogger(__name__)

def _slice(key: str) -> str:
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")

def _planning(key: str) -> str:
    i18n = _get_i18n()
    return i18n.get(f"planning.{key}")

class StandardPromptResult(BaseModel):

    prompt: str = Field(default="")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) and getattr(self, key) is not None


def format_conversation(
    chat_history,
    newest_first: bool = False,
):
    messages = [
        m
        for m in chat_history
        if isinstance(m, dict)
        and "role" in m
        and "content" in m
    ]

    if newest_first:
        messages.reverse()

    lines = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        lines.append(f"{role}: {content}")

    return "\n".join(lines)

    

def build_task_prompt(
    description: str,
    expected_output: str | None = None, 
) -> str:

    task_slice = _slice("task")
    
    parts = [task_slice.format(input=description)]

    if expected_output:
        output_slice = _slice("expected_output")
        parts.append(output_slice.format(expected_output=expected_output))

    return "\n\n".join(parts)


def build_chat_prompt(chat_history: list[dict] | None = None) -> str:
    parts:list = []

    if chat_history:
        instruction = _slice("conversation_history_instruction").replace("{history}",format_conversation(chat_history))
        parts.append(f"{instruction}")
        parts.append(_slice("conversational_answer_from_history_prompt"))

    return "\n\n".join(parts)

def build_task_prompt_with_schema(
    output_json: type | None = None,
    output_pydantic: type | None = None,
    response_model: type | None = None,
) -> str:
    
    prompt = ''
    if (output_json or output_pydantic) and not response_model:
        target = output_json or output_pydantic
        schema_dict = generate_model_description(target)
        if isinstance(schema_dict, list):
            parts = [json.dumps(s["json_schema"]["schema"], indent=2) for s in schema_dict]
            schema = "\n\n".join(parts)
        else:
            schema = json.dumps(schema_dict["json_schema"]["schema"], indent=2)
        prompt += "\n" + _slice("formatted_task_instructions").format(
            output_format=schema
        )
    return  prompt


def build_task_context(task_prompt: str, context: str | None) -> str:
    if context:
        task_with_context = _slice("task_with_context")
        return task_with_context.format(task=task_prompt, context=context)
    return task_prompt


async def prepare_task_prompt(
    description: str,
    expected_output: str | None = None,
    chat_history: list[dict] | None = None,
    context: str | None = None,
    output_json: type | None = None,
    output_pydantic: type | None = None,
    response_model: type | None = None
) -> str:

    task_prompt = build_task_prompt(
        description=description,
        expected_output=expected_output
    )

    task_prompt += build_task_prompt_with_schema(
        output_json=output_json,
        output_pydantic=output_pydantic,
        response_model=response_model,
    )
    
    task_prompt += build_chat_prompt(chat_history=chat_history)
  

    task_prompt += build_task_context(task_prompt, context)

    return task_prompt


async def prepare_planner_task_prompt(
    description: str,
    output_json: type | None = None,
    output_pydantic: type | None = None,
    max_steps : int = 4,
) -> str:

    parts = _planning("create_plan_prompt").replace("{description}",description)\
    .replace("{max_steps}",str(max_steps))

    parts += "\n\n" + build_task_prompt_with_schema(
        output_json=output_json,
        output_pydantic=output_pydantic
    )

    return parts

async def prepare_planner_system_prompt(tools: list[Any] = [], agent: dict = {}):
    return _planning('system_prompt')

async def prepare_system_prompt(max_thinking_steps:int,tools: list[Any] = [], agent: Any = None):
    
    slices = ["role_playing","max_thinking_steps"]

    if len(tools) > 0:
        slices.append("tools")
        slices.append("format")
        slices.append("format_without_tools")
        
    else:
        slices.append("no_tools")
    
    prompt = ''.join([
            f"{_slice(slice)}\n\n" for slice in slices
    ])

    prompt = prompt.replace("{goal}",agent.goal)\
             .replace("{role}", agent.role)\
             .replace("{backstory}",agent.backstory)\
             .replace('{tools}',tools_schema_and_description(tools))\
             .replace('{max_steps}',str(max_thinking_steps))\
             .replace('{no_tools}',"")


    stop_words = [_slice("observation")]
    return  prompt, stop_words

