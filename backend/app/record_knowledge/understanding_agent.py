

import json
import logging
import re
from typing import TypedDict

import dirtyjson
from pydantic import BaseModel, Field

from app.agents.specs.record_insight.agent import RecordInsightAgent
from app.lib.json_parser import parse_json_output
from app.lib.pydantic_schema_utils import generate_model_description
from app.runtime import AgentRuntime, ToolBinder
from app.lib.i18n import _get_i18n


logger = logging.getLogger(__name__)

_agent = RecordInsightAgent()

def _slice(key: str) -> str:
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")

class UnderstandingResult(TypedDict):
    insight: str
    suggestions: list[str]


class UnderstandingOutput(BaseModel):
    insight: str = Field(description="A condensed comprehensive overview of all retrieved information.")
    suggestions: list[str] = Field(description="Exactly 2 short follow-up questions. Each must be 30 characters or fewer.", max_length=2)


FINAL_ANSWER_PATTERN = re.compile(r"<Final Answer>(.*?)(?:</Final Answer>|$)", re.DOTALL)
_OUTPUT_SCHEMA = generate_model_description(UnderstandingOutput)
_OUTPUT_FORMAT_DESC = json.dumps(_OUTPUT_SCHEMA["json_schema"]["schema"], indent=2)

# SYSTEM_PROMPT = (
#     # "You are an autonomous agent.\n\n"
#     "Retrieve ALL available information before answering:\n"
#     "Write one complete, natural explanation of the information.\n"
#     "- Focus on the subject, purpose, and important details.\n"
#     "- Combine related information into one coherent overview.\n"
#     "- Include important people, organisations, dates, places, amounts, and other key facts when relevant.\n"
#     "- If an image's visual content is available, naturally incorporate what it shows.\n"
#     "- Ignore image encodings, base64 strings, MIME types, metadata, filenames, URLs, formatting, layout, and storage details.\n"
#     "- If only an image reference exists without visible content, ignore it instead of describing it.\n"
#     "- Describe the meaning of the information, never its representation.\n"
#     "- Do not invent, infer, enrich, or embellish information.\n"
#     "- If information is unavailable, clearly state that it is unavailable.\n\n"
#     "Write as though the explanation was written independently.\n"
#     "The reader should never know the information came from retrieved material.\n"
#     "Never refer to or describe where the information came from, how it was stored, retrieved, formatted, structured, or represented.\n"
#     "Begin immediately with the topic itself.\n\n"
# )

SYSTEM_PROMPT = (
    """
    Give comprehensive Overview
    """
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
        "suggestions": list(data.get("suggestions", [])),
    }


async def run_understanding_agent(business_id: str, record_id: str) -> UnderstandingResult:

    prompt = "Fetch write comprehensive overview of it from current knowledge system"
    #f"/business/{business_id}", 
    scopes = [f"/{business_id}/record/{record_id}"]
    _agent.bind_tools(business_id)
    response = await _agent.execute_agent(SYSTEM_PROMPT)
    print(response)

    response =  parse_json_output(response.result.response)
    print(response)
    if response:
        return response

    return {"insight": '', "suggestions": []}
