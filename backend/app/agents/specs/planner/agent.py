from typing import Any

from app.execution.models import Result

try:
    from app.agents.models import Agent
    _spec = Agent.from_spec("planner")
except Exception:
    _spec = None


class PlannerAgent:
    agent_id = "planner"
    goal = _spec.goal if _spec else "Route user requests to the correct domain agents and build execution plans"
    role = _spec.role if _spec else "planner agent"
    backstory = _spec.backstory if _spec else "You are a routing agent that decides which agents should handle the user's request."

    def get_tools(self, business_id: str, scopes: list[str] | None = None) -> list[Any]:
        return []
