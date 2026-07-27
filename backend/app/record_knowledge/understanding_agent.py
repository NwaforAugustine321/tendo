"""Understanding agent — uses AgentRuntime for generating record overviews."""

import json
import logging
import re
from typing import TypedDict

import dirtyjson
from pydantic import BaseModel, Field

from app.lib.json_parser import parse_json_output
from app.lib.pydantic_schema_utils import generate_model_description
from app.runtime import AgentRuntime, ToolBinder

logger = logging.getLogger(__name__)

FINAL_ANSWER_PATTERN = re.compile(r"<Final Answer>(.*?)(?:</Final Answer>|$)", re.DOTALL)


class UnderstandingResult(TypedDict):
    insight: str
    suggested_questions: list[str]


class UnderstandingOutput(BaseModel):
    insight: str = Field(description="A condensed comprehensive overview of all retrieved information.")
    suggestions: list[str] = Field(description="Exactly 2 short follow-up questions. Each must be 30 characters or fewer.", max_length=2)


_OUTPUT_SCHEMA = generate_model_description(UnderstandingOutput)
_OUTPUT_FORMAT_DESC = json.dumps(_OUTPUT_SCHEMA["json_schema"]["schema"], indent=2)

SYSTEM_PROMPT = (
    "You are an autonomous agent.\n\n"
    "Retrieve ALL available information before answering:\n"
    "1. Call count_knowledge.\n"
    "2. Fetch all records with fetch_knowledge using dynamically calculated pages. Track offsets to avoid duplicate reads.\n"
    "3. Use search_knowledge only when additional context is needed.\n\n"
    "Write one complete, natural explanation of the information.\n"
    "- Focus on the subject, purpose, and important details.\n"
    "- Combine related information into one coherent overview.\n"
    "- Include important people, organisations, dates, places, amounts, and other key facts when relevant.\n"
    "- If an image's visual content is available, naturally incorporate what it shows.\n"
    "- Ignore image encodings, base64 strings, MIME types, metadata, filenames, URLs, formatting, layout, and storage details.\n"
    "- If only an image reference exists without visible content, ignore it instead of describing it.\n"
    "- Describe the meaning of the information, never its representation.\n"
    "- Do not invent, infer, enrich, or embellish information.\n"
    "- If information is unavailable, clearly state that it is unavailable.\n\n"
    "Write as though the explanation was written independently.\n"
    "The reader should never know the information came from retrieved material.\n"
    "Never refer to or describe where the information came from, how it was stored, retrieved, formatted, structured, or represented.\n"
    "Begin immediately with the topic itself.\n\n"
    "Wrap the final response in <Final Answer>...</Final Answer>.\n"
    "Inside the tags, return ONLY a JSON object matching the schema below.\n"
    f"{_OUTPUT_FORMAT_DESC}\n\n"
    "Example:\n"
    '{"insight":"Comprehensive explanation.",'
    '"suggestions":["Question 1","Question 2"]}\n\n'
    "Rules:\n"
    "- insight: one unified explanation, not a list of records or documents.\n"
    "- suggestions: exactly 2 follow-up questions, each 30 characters or fewer.\n"
    "- Return only the JSON object inside <Final Answer> tags."
)


def _extract_final_answer(text: str) -> UnderstandingResult | None:
    match = FINAL_ANSWER_PATTERN.search(text)
    if not match:
        return None
    content = match.group(1).strip()
    try:
        data = dirtyjson.loads(content)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return {
        "insight": data.get("insight", ""),
        "suggested_questions": list(data.get("suggestions", [])),
    }


async def run_understanding_agent(business_id: str, record_id: str) -> UnderstandingResult:
    from app.llm.client import get_client
    from app.runtime.tool_registry import build_tool_registry
    from app.memory.tools import get_knowledge_tools

    all_tools = get_knowledge_tools(business_id, scopes=None)
    registry = build_tool_registry(tools=all_tools)

    llm = get_client()
    tool_binder = ToolBinder(tool_registry=registry)

    runtime = AgentRuntime(
        llm=llm,
        tool_binder=tool_binder,
        max_iter=25,
    )

    # Set up runtime state with system prompt and tools
    from app.contexts.models import ToolReference
    from app.lib.tool_schema import tools_schema_and_description

    bound_tools = await tool_binder.bind([
        ToolReference(tool_id=name, capability=name) for name in registry
    ])
    runtime._tools = bound_tools
    runtime._tools_names = ", ".join(t.name for t in bound_tools)
    runtime._tools_description = tools_schema_and_description(bound_tools)
    runtime._iterations = 0
    runtime._tool_call_history = set()

    # Bind tools to LLM for native tool calling
    try:
        runtime._llm = llm.bind_tools(bound_tools)
    except Exception:
        pass

    runtime._messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Fetch all available information and give me a comprehensive overview."},
    ]

    raw = await runtime._invoke_loop()

    result = _extract_final_answer(raw)
    if result:
        return result

    return {"insight": raw, "suggested_questions": []}
