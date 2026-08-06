

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


SYSTEM_PROMPT = (
    """
    Give comprehensive Overview
    """
)



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
