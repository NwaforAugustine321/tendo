"""Domain Agent Protocol — interface every domain agent must implement."""

from typing import Protocol, runtime_checkable

from app.contexts.models import ExecutionContext, SharedContext
from app.execution.models import DomainResult


@runtime_checkable
class DomainAgentProtocol(Protocol):
    """Interface every domain agent must implement."""

    async def reason(
        self,
        execution_context: ExecutionContext,
        shared_context: SharedContext,
    ) -> DomainResult: ...
