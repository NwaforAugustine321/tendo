"""Business Knowledge Agent — public API (renamed from app.intelligence)."""

from app.business_knowledge.agent import process_events
from app.business_knowledge.config import IntelligenceConfig, get_intelligence_config
from app.business_knowledge.models import (
    AgentError,
    AgentStatus,
    ExecutionError,
    InsightEntry,
    InsightOutput,
    IntelligenceError,
)
from app.business_knowledge.persistence import InsightPersistence
from app.business_knowledge.tools import INTELLIGENCE_TOOLS

__all__ = [
    "process_events",
    "IntelligenceConfig",
    "get_intelligence_config",
    "AgentStatus",
    "InsightEntry",
    "InsightOutput",
    "IntelligenceError",
    "AgentError",
    "ExecutionError",
    "InsightPersistence",
    "INTELLIGENCE_TOOLS",
]
