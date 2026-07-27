"""Understanding agent — LangChain stateful agent for generating record overviews."""

import asyncio
import json
import logging
import re
from typing import TypedDict
import dirtyjson
from json_repair import repair_json
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.memory.tools import get_record_knowledge_tools
from app.llm.client import get_client as get_llm_client
from app.lib.pydantic_schema_utils import generate_model_description

logger = logging.getLogger(__name__)


FINAL_ANSWER_PATTERN = re.compile(r"<Final Answer>(.*?)(?:</Final Answer>|$)", re.DOTALL)



class AgentState(TypedDict):
    messages: list[BaseMessage]
    final_answer: str


class UnderstandingResult(TypedDict):
    insight: str
    suggested_questions: list[str]


class UnderstandingOutput(BaseModel):
    """The final output format for record understanding."""
    insight: str = Field(description="A condensed comprehensive overview of all retrieved information. Write specific details, not generic descriptions.")
    suggestions: list[str] = Field(description="Exactly 2 short follow-up questions. Each must be 30 characters or fewer.", max_length=2)


# Generate schema description for the LLM
_OUTPUT_SCHEMA = generate_model_description(UnderstandingOutput)
_OUTPUT_FORMAT_DESC = json.dumps(_OUTPUT_SCHEMA["json_schema"]["schema"], indent=2)


SYSTEM_PROMPT = (
    "You are an autonomous agent.\n\n"

    "Retrieve ALL available information before answering:\n"
    "1. Call count_row.\n"
    "2. Fetch all records with fetch using dynamically calculated pages. Track offsets to avoid duplicate reads.\n"
    "3. Use search_information only when additional context is needed.\n\n"

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
    "The schema is for reference only; return actual values.\n\n"
    f"{_OUTPUT_FORMAT_DESC}\n\n"

    "Example:\n"
    "{\"insight\":\"Comprehensive explanation.\","
    "\"suggestions\":[\"Question 1\",\"Question 2\"]}\n\n"

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

    data = dirtyjson.loads(content)

    # dirtyjson may return a string if content isn't valid JSON object
    if not isinstance(data, dict):
        return None

    return {
        "insight": data["insight"],
        "suggested_questions": list(data.get("suggestions", [])),
    }




async def run_understanding_agent(business_id: str, record_id: str) -> UnderstandingResult:

    tools = get_record_knowledge_tools(business_id, record_id)
    llm = get_llm_client()
    llm_with_tools = llm.bind_tools(tools)
    # llm.with_thinking_mode(enabled=False)

    state: AgentState = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="Fetch all available information and give me a comprehensive overview."),
        ],
        "final_answer": "",
    }

    while True:
        try:
            response = await llm_with_tools.ainvoke(state["messages"])
        except Exception as e:
            if "Timeout" in str(e) or "timeout" in str(e):
                logger.warning(f"LLM timeout, retrying: {e}")
                wait_time = 2
                await asyncio.sleep(wait_time)
                continue
            # Handle context length exceeded — summarize messages and retry
            from app.lib.context_handler import is_context_length_exceeded, summarize_messages
            if is_context_length_exceeded(e):
                logger.warning(f"Context length exceeded, summarizing messages: {e}")
                state["messages"] = await summarize_messages(
                    [{"role": getattr(m, "type", "user"), "content": getattr(m, "content", "")} for m in state["messages"]]
                )
                continue
            raise

        if not response.tool_calls:
            raw = response.content if hasattr(response, "content") else str(response)

            result = _extract_final_answer(raw)
            if result:
                return result

            state["messages"].append(AIMessage(content=raw))
            continue

        # Execute all tool calls in parallel
        state["messages"].append(response)
        print(response.tool_calls)
        async def _execute_tool(tc):
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_fn = next((t for t in tools if t.name == tool_name), None)
            if not tool_fn:
                return ToolMessage(content="Tool not found.", tool_call_id=tc["id"])
            result = await tool_fn.ainvoke(tool_args)
            result_str = str(result)

            # If paged fetch result contains images, build multimodal content blocks
            if tool_name == "record_knowledge_paged_fetch":
                try:
                    parsed = json.loads(result_str)
                    has_images = False
                    if isinstance(parsed, list):
                        for page_result in parsed:
                            for entry in page_result.get("entries", []):
                                if entry.get("images"):
                                    has_images = True
                                    break
                            if has_images:
                                break

                    if has_images:
                        content_blocks = []
                        # Add the text result first (without images to keep text clean)
                        text_entries = []
                        image_urls = []
                        for page_result in parsed:
                            for entry in page_result.get("entries", []):
                                text_entries.append({"content": entry.get("content", "")})
                                for img_url in entry.get("images", []):
                                    image_urls.append(img_url)

                        content_blocks.append({"type": "text", "text": result_str})
                        for img_url in image_urls:
                            content_blocks.append({"type": "image_url", "image_url": {"url": img_url}})

                        return ToolMessage(content=content_blocks, tool_call_id=tc["id"])
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass

            return ToolMessage(content=result_str, tool_call_id=tc["id"])

        tool_messages = await asyncio.gather(*[_execute_tool(tc) for tc in response.tool_calls])


        state["messages"].extend(tool_messages)
            
