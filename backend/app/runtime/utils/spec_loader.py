from __future__ import annotations
from pathlib import Path
from typing import Protocol, runtime_checkable
from pydantic import BaseModel, Field
from app.config.settings import settings
from app.contexts.models import ExecutionContext, SharedContext
from app.execution.models import Result

from pathlib import Path


SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "agents" / "specs"


class LoaderAgentSpec(BaseModel):
    """Loaded agent spec files.

    Usage:
        agent = Agent.from_spec("domain/inventory")
        agent.role       # content of role.md
        agent.goal       # content of goal.md
        agent.backstory  # content of backstory.md
    """

    role: str = Field(description="Agent role (from role.md)")
    goal: str = Field(description="Agent goal (from goal.md)")
    backstory: str = Field(description="Agent backstory (from backstory.md)")
    expected_output: str = Field(
        default="", description="Expected output format (from output.md)")
    name: str = Field(default='', description="Agent name (from settings)")

    @classmethod
    def from_spec(cls, name: str, path: str) -> LoaderAgentSpec:

        spec_dir = SPECS_DIR / path

        if not spec_dir.is_dir():
            raise FileNotFoundError(
                f"No spec directory found for {name} agent. Path: {spec_dir}")

        def _read(filename: str) -> str:
            path = spec_dir / filename
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
            return ""

        return cls(
            role=_read("role.md"),
            goal=_read("goal.md"),
            backstory=_read("backstory.md"),
            expected_output=_read("output.md"),
            name=name
        )
