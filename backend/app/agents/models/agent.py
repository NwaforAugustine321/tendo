"""Agent model — holds spec-loaded attributes for prompt building."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from app.config.settings import settings

SPECS_DIR = Path(__file__).parent.parent / "specs"


class Agent(BaseModel):
    """An agent loaded from spec files.

    Holds role, goal, backstory, and expected_output read from the
    agent's spec directory. Used by Prompts and AgentExecutor.

    Usage:
        agent = Agent.from_spec("domain/inventory")
        agent.role       # content of role.md
        agent.goal       # content of goal.md
        agent.backstory  # content of backstory.md
    """

    role: str = Field(description="Agent role (from role.md)")
    goal: str = Field(description="Agent goal (from goal.md)")
    backstory: str = Field(description="Agent backstory (from backstory.md)")
    expected_output: str = Field(default="", description="Expected output format (from output.md)")
    skill: str = Field(default="", description="Agent skills/instructions (from skill.md)")

    @classmethod
    def from_spec(cls, spec_name: str) -> Agent:
        """Load an Agent from spec markdown files.

        Args:
            spec_name: Path relative to specs dir (e.g., "domain/inventory").

        Returns:
            An Agent instance with fields populated from .md files.
        """
        spec_dir = SPECS_DIR / spec_name

        if not spec_dir.is_dir():
            raise FileNotFoundError(f"No spec directory found: {spec_dir}")

        def _read(filename: str) -> str:
            path = spec_dir / filename
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                return content.replace("{AGENT_NAME}", settings.agent_name)
            return ""

        return cls(
            role=_read("role.md"),
            goal=_read("goal.md"),
            backstory=_read("backstory.md"),
            expected_output=_read("output.md"),
            skill=_read("skill.md"),
        )
