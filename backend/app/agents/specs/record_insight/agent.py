from typing import Any

from app.execution.models import Result

try:
    from app.agents.models import Agent
    _spec = Agent.from_spec("record_insight")
except Exception:
    _spec = None


class RecordInsightAgent:
    agent_id = "record_insight"
    goal = _spec.goal if _spec else "Generate comprehensive overviews of stored record knowledge"
    role = _spec.role if _spec else "record insight agent"
    backstory = _spec.backstory if _spec else "You retrieve all available information and produce a unified, natural explanation."

    def get_tools(self, business_id: str, scopes: list[str] | None = None) -> list[Any]:
        from app.memory.tools import get_knowledge_tools
        return get_knowledge_tools(business_id=business_id, scopes=scopes)
