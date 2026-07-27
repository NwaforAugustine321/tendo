from typing import Any

from app.contexts.models import ExecutionContext, SharedContext
from app.execution.models import DomainResult


class KnowledgeAgent:
    agent_id = "knowledge"

    def get_tools(self, business_id: str, scopes: list[str] | None = None) -> list[Any]:
        from app.db.tools.profile_tools import get_profile_tools
        from app.memory.tools import get_knowledge_tools

        return get_profile_tools(business_id) + get_knowledge_tools(business_id=business_id, scopes=scopes)

    async def reason(
        self, execution_context: ExecutionContext, shared_context: SharedContext
    ) -> DomainResult:
        return DomainResult(
            payload={"domain": "knowledge"},
            status="success",
            response_text=execution_context.objective,
        )
