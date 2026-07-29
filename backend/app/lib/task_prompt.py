
from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING
from app.lib.i18n import _get_i18n
from app.lib.pydantic_schema_utils import generate_model_description
if TYPE_CHECKING:
    from app.memory.memory import Memory

logger = logging.getLogger(__name__)


def _slice(key: str) -> str:
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")


from typing import Iterable, Mapping, Any


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

    

def prompt(
    description: str,
    expected_output: str | None = None,
    chat_history: list[dict] | None = None,
) -> str:

    task_slice = _slice("task")
    parts = [task_slice.format(input=description)]

    if chat_history:
        instruction = _slice("conversation_history_instruction").replace("{history}",format_conversation(chat_history))
        parts.append(f"{instruction}")

    if expected_output:
        output_slice = _slice("expected_output")
        parts.append(output_slice.format(expected_output=expected_output))

    return "\n\n".join(parts)


def build_task_prompt_with_schema(
    task_prompt: str,
    output_json: type | None = None,
    output_pydantic: type | None = None,
    response_model: type | None = None,
) -> str:

    if (output_json or output_pydantic) and not response_model:
        if output_json:
            schema_dict = generate_model_description(output_json)
            schema = json.dumps(schema_dict["json_schema"]["schema"], indent=2)
            task_prompt += "\n" + _slice("formatted_task_instructions").format(
                output_format=schema
            )
        elif output_pydantic:
            schema_dict = generate_model_description(output_pydantic)
            schema = json.dumps(schema_dict["json_schema"]["schema"], indent=2)
            task_prompt += "\n" + _slice("formatted_task_instructions").format(
                output_format=schema
            )
    return task_prompt


def format_task_with_context(task_prompt: str, context: str | None) -> str:

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
    response_model: type | None = None,
) -> str:

    task_prompt = prompt(
        description=description,
        expected_output=expected_output,
        chat_history=chat_history,
    )

    task_prompt = build_task_prompt_with_schema(
        task_prompt=task_prompt,
        output_json=output_json,
        output_pydantic=output_pydantic,
        response_model=response_model,
    )

    task_prompt = format_task_with_context(task_prompt, context)

    return task_prompt
