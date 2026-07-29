"""Tests for AgentRuntime.execute() lifecycle."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.execution.models import Execution, Result, ReflectionOutput
from app.runtime.agent_runtime import AgentRuntime
from app.runtime.tool_binder import ToolBinder


def _make_runtime(
    objective: str = "Do something",
    tool_binder: ToolBinder | None = None,
    reflection_stage=None,
    domain_agent=None,
) -> AgentRuntime:
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    binder = tool_binder or ToolBinder()
    if domain_agent is None:
        domain_agent = MagicMock()
        domain_agent.agent_id = "test-agent"
    return AgentRuntime(
        llm=llm,
        tool_binder=binder,
        domain_agent=domain_agent,
        objective=objective,
        reflection_stage=reflection_stage,
    )


@pytest.mark.asyncio
async def test_execute_valid_context_returns_agent_execution():
    runtime = _make_runtime()

    result = await runtime.execute()

    assert isinstance(result, Execution)
    assert result.agent_id == "test-agent"
    assert result.error is None
    assert result.metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_execute_empty_objective_returns_error():
    """Runtime with whitespace-only objective should return error without invoking agent."""
    runtime = _make_runtime(objective="   ")

    result = await runtime.execute()

    assert result.error is not None
    assert "objective" in result.error.lower()
    assert result.result.status == "failure"


@pytest.mark.asyncio
async def test_execute_uses_agent_class_name_when_no_agent_id():
    class MyDomainAgent:
        pass

    runtime = _make_runtime(domain_agent=MyDomainAgent())
    result = await runtime.execute()

    assert result.agent_id == "MyDomainAgent"


@pytest.mark.asyncio
async def test_execute_calls_tool_binder_bind_and_release():
    binder = ToolBinder()
    binder.bind = AsyncMock(return_value=[])
    binder.release = AsyncMock()
    runtime = _make_runtime(tool_binder=binder)

    await runtime.execute()

    binder.bind.assert_called_once()
    binder.release.assert_called_once()


@pytest.mark.asyncio
async def test_execute_successful_reflection():
    expected_reflection = ReflectionOutput(
        confidence=0.9,
        observations=["good execution"],
    )
    reflection_stage = AsyncMock()
    reflection_stage.reflect = AsyncMock(return_value=expected_reflection)
    runtime = _make_runtime(reflection_stage=reflection_stage)

    result = await runtime.execute()

    assert result.reflection.confidence == 0.9
    assert result.reflection.observations == ["good execution"]
    reflection_stage.reflect.assert_called_once()
