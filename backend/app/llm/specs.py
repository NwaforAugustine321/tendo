"""Agent spec loader — reads .md configuration files and assembles system prompts."""

from dataclasses import dataclass
from pathlib import Path

SPECS_DIR = Path(__file__).parent.parent / "agents" / "specs"
ASSEMBLY_ORDER = ["role", "backstory", "goal", "skill", "tools"]

_cache: dict[str, "AgentConfig"] = {}


@dataclass
class AgentConfig:
    system_prompt: str
    agent_name: str
    has_tools: bool


def load(agent_name: str) -> AgentConfig:
    """Load agent spec from .md files. Assembly order: role → backstory → goal → skill → tools."""
    from app.config.settings import settings

    if not settings.spec_hot_reload and agent_name in _cache:
        return _cache[agent_name]

    spec_dir = SPECS_DIR / agent_name
    if not spec_dir.is_dir():
        raise FileNotFoundError(f"No spec directory found for agent: {agent_name}")

    parts: list[str] = []
    has_tools = False

    for section in ASSEMBLY_ORDER:
        file = spec_dir / f"{section}.md"
        if file.exists():
            content = file.read_text(encoding="utf-8").strip()
            if content:
                parts.append(f"## {section.upper()}\n\n{content}")
            if section == "tools":
                has_tools = True

    if not parts:
        raise ValueError(f"Agent spec '{agent_name}' has no content in any .md file")

    system_prompt = "\n\n".join(parts)
    config = AgentConfig(system_prompt=system_prompt, agent_name=agent_name, has_tools=has_tools)

    if not settings.spec_hot_reload:
        _cache[agent_name] = config

    return config
