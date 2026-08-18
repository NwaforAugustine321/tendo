
from typing import Any
from app.runtime import AgentRuntime, ToolBinder
from app.execution.models import Result
from app.db.tools.profile_tools import get_profile_tools
from app.memory.tools import get_knowledge_tools
from app.guardrails import GuardrailManager, GuardrailConfig
from pydantic import BaseModel, Field

try:
    from app.agents.models import Agent
    agent_spec = Agent.from_spec("record_insight")
except Exception:
    agent_spec = None



class UnderstandingOutput(BaseModel):
    insight: str = Field(description="A condensed comprehensive overview of all retrieved information.")
    suggestions: list[str] = Field(description="Exactly 2 short follow-up questions. Each must be 30 characters or fewer.", max_length=2)


class RecordInsightAgent:

    def __init__(self):
        self._runtime = AgentRuntime(
                agent=agent_spec,
                tool_binder=ToolBinder(),
                output_pydantic=UnderstandingOutput,
                expected_output='Return json output',
                max_token=2000
        )

    def bind_tools(self, business_id: str, scopes: list[str] = []) -> list[Any]:
        self._runtime.bind_tool( get_knowledge_tools(business_id=business_id, scopes=scopes))

    async def execute_agent(self, *args, **kwargs):
        return await self._runtime.execute(*args, **kwargs)
