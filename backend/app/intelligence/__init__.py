"""Business Intelligence Agent — public API."""

from app.intelligence.agent import process_events
from app.intelligence.config import IntelligenceConfig, get_intelligence_config
from app.intelligence.models import (
    AgentError,
    AgentStatus,
    ExecutionError,
    InsightEntry,
    InsightOutput,
    IntelligenceError,
)
from app.intelligence.persistence import InsightPersistence
from app.intelligence.tools import INTELLIGENCE_TOOLS

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
