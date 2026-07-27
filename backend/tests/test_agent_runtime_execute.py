"""Tests for AgentRuntime.execute() lifecycle."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.contexts.models import ExecutionContext, SharedContext, OutputSpec, ToolReference
from app.execution.models import AgentExecution, DomainResult, ReflectionOutput
from app.runtime.agent_runtime import AgentRuntime
from app.runtime.tool_binder import ToolBinder


def _make_ec(objective: str = "Do something", tools: list | None = None) -> ExecutionContext:
    return ExecutionContext(
        objective=objective,
        expected_output=OutputSpec(format="text"),
        available_tools=tools or [],
    )


def _make_sc() -> SharedContext:
    return SharedContext(user_request="hello", business_id="biz-1")


def _make_runtime(
    tool_binder: ToolBinder | None = None,
    reflection_stage=None,
) -> AgentRuntime:
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    binder = tool_binder or ToolBinder()
    return AgentRuntime(
        llm=llm,
        tool_binder=binder,
        reflection_stage=reflection_stage,
    )


@pytest.mark.asyncio
async def test_execute_valid_context_returns_agent_execution():
    runtime = _make_runtime()
    ec = _make_ec()
    sc = _make_sc()
    agent = AsyncMock()
    agent.agent_id = "test-agent"
    agent.reason = AsyncMock(return_value=DomainResult(payload={"key": "val"}, status="success"))

    result = await runtime.execute(ec, sc, agent)

    assert isinstance(result, AgentExecution)
    assert result.agent_id == "test-agent"
    assert result.result.status == "success"
    assert result.result.payload == {"key": "val"}
    assert result.error is None
    assert result.metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_execute_empty_objective_returns_error():
    """EC with whitespace-only objective should return error without invoking agent."""
    runtime = _make_runtime()
    ec = ExecutionContext(
        objective="   ",
        expected_output=OutputSpec(format="text"),
    )
    sc = _make_sc()
    agent = AsyncMock()
    agent.agent_id = "test-agent"
    agent.reason = AsyncMock()

    result = await runtime.execute(ec, sc, agent)

    assert result.error is not None
    assert "objective" in result.error.lower()
    assert result.result.status == "failure"
    agent.reason.assert_not_called()


@pytest.mark.asyncio
async def test_execute_domain_agent_failure_returns_error():
    runtime = _make_runtime()
    ec = _make_ec()
    sc = _make_sc()
    agent = AsyncMock()
    agent.agent_id = "failing-agent"
    agent.reason = AsyncMock(side_effect=RuntimeError("boom"))

    result = await runtime.execute(ec, sc, agent)

    assert result.error is not None
    assert "boom" in result.error
    assert result.result.status == "failure"
    assert result.metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_execute_reflection_failure_returns_empty_reflection():
    reflection_stage = AsyncMock()
    reflection_stage.reflect = AsyncMock(side_effect=Exception("reflect failed"))
    runtime = _make_runtime(reflection_stage=reflection_stage)
    ec = _make_ec()
    sc = _make_sc()
    agent = AsyncMock()
    agent.agent_id = "agent-1"
    agent.reason = AsyncMock(return_value=DomainResult(payload={}, status="success"))

    result = await runtime.execute(ec, sc, agent)

    assert result.error is None
    assert result.reflection == ReflectionOutput()
    assert result.result.status == "success"


@pytest.mark.asyncio
async def test_execute_calls_tool_binder_bind_and_release():
    binder = ToolBinder()
    binder.bind = AsyncMock(return_value=[])
    binder.release = AsyncMock()
    runtime = _make_runtime(tool_binder=binder)
    ec = _make_ec(tools=[ToolReference(tool_id="t1", capability="search")])
    sc = _make_sc()
    agent = AsyncMock()
    agent.agent_id = "agent"
    agent.reason = AsyncMock(return_value=DomainResult())

    await runtime.execute(ec, sc, agent)

    binder.bind.assert_called_once_with(ec.available_tools)
    binder.release.assert_called_once()


@pytest.mark.asyncio
async def test_execute_releases_tools_even_on_agent_failure():
    binder = ToolBinder()
    binder.bind = AsyncMock(return_value=[])
    binder.release = AsyncMock()
    runtime = _make_runtime(tool_binder=binder)
    ec = _make_ec()
    sc = _make_sc()
    agent = AsyncMock()
    agent.agent_id = "agent"
    agent.reason = AsyncMock(side_effect=ValueError("oops"))

    await runtime.execute(ec, sc, agent)

    binder.release.assert_called_once()


@pytest.mark.asyncio
async def test_execute_uses_agent_class_name_when_no_agent_id():
    runtime = _make_runtime()
    ec = _make_ec()
    sc = _make_sc()

    class MyDomainAgent:
        async def reason(self, execution_context, shared_context):
            return DomainResult(payload={"done": True})

    agent = MyDomainAgent()
    result = await runtime.execute(ec, sc, agent)

    assert result.agent_id == "MyDomainAgent"


@pytest.mark.asyncio
async def test_execute_successful_reflection():
    expected_reflection = ReflectionOutput(
        confidence=0.9,
        observations=["good execution"],
    )
    reflection_stage = AsyncMock()
    reflection_stage.reflect = AsyncMock(return_value=expected_reflection)
    runtime = _make_runtime(reflection_stage=reflection_stage)
    ec = _make_ec()
    sc = _make_sc()
    agent = AsyncMock()
    agent.agent_id = "agent"
    agent.reason = AsyncMock(return_value=DomainResult(payload={"x": 1}))

    result = await runtime.execute(ec, sc, agent)

    assert result.reflection.confidence == 0.9
    assert result.reflection.observations == ["good execution"]
    reflection_stage.reflect.assert_called_once()
