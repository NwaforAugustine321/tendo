from __future__ import annotations

import asyncio
import logging
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from app.manifests import load_manifest
from app.runtime import AgentRuntime, ToolBinder
from app.agents.specs.domain import TransactionsAgent, InventoryAgent, KnowledgeAgent
from app.db.tools.messages import save_messages
from app.memory.memory import Memory
from app.runtime.agents.agent import Agent
from app.runtime.agents.middleware import AgentMiddleware
from app.runtime.toolsets.executor import ToolExecutionResult
from app.toolsets import function_tool
from app.llm.client import get_client
from app.runtime.llm_vendors.langchain import LangChainLLM

_llm = get_client()

llm = LangChainLLM(
    model=_llm
)

logger = logging.getLogger(__name__)

try:
    from app.agents.models import Agent as AgentModel
    agent_spec = AgentModel.from_spec("planner")
except Exception:
    agent_spec = None


@function_tool
async def get_weather(
    city: str,
) -> str:
    """
    Get the weather for a city.
    """

    return f"{city}: 28°C Sunny"


class ToolLoggingMiddleware(AgentMiddleware):
    """Logs tool calls and their results."""

    async def before_tools(self, ctx, tool_calls) -> None:

        logger.info("[middleware] Tool execution starting...")
        print(tool_calls)
        print('\n\n')

    async def after_tools(self, ctx, results: list[ToolExecutionResult]) -> None:
        for r in results:
            logger.info(
                "tool result"
            )
            print(r.output)
            print('\n')


class SelectedAgent(BaseModel):
    agent_id: str = Field(default_factory=str, description="Agent id.")
    depends_on: list = Field(
        default_factory=list[str], description="List of agent_id the agent depend on")
    message_input: str = Field(..., min_length=1,
                               description="Clear instruction for what the agent must accomplish")


class AgentSelectionOutput(BaseModel):
    agents: list[SelectedAgent] = Field(
        default_factory=list, description="List of agents to handle the request. Each has agent_id, execution_context, and depends_on.")
    shared_constraints: str = Field(
        default_factory=str, description="Shared constraints for all agents execution")


class PlanningError(Exception):
    def __init__(self, message: str, manifest: str | None = None):
        super().__init__(message)
        self.manifest = manifest


global registry

registry = {
    "transaction_agent": TransactionsAgent(),
    "inventory_agent": InventoryAgent(),
    "general_information_agent": KnowledgeAgent(),
}


def delegate_to_agents(session: dict | None = {}):

    @tool
    async def _tool(
        agents: list[SelectedAgent],
        shared_constraints: str = "",
    ) -> str:
        """Delegate tasks to specialized sub-agents for execution.

           Args:
              agents: List of agent assignments. Each must have:
                - agent_id: One of "transaction_agent", "inventory_agent", "general_information_agent"
                - message_input: Clear instruction for what the agent must accomplish
                - depends_on: List of agent_ids this agent depends on
              shared_constraints: Constraints that apply to all agents.

            Return:
              - str
        """

        has_dependencies = any(
            len(a.depends_on) > 0 for a in agents if hasattr(a, 'depends_on')
        )

        agent_dicts = [a.model_dump() if hasattr(
            a, 'model_dump') else a for a in agents]

        if has_dependencies:
            asyncio.create_task(_run_sequential(
                agent_dicts, shared_constraints, session=session))
        else:
            asyncio.create_task(_run_parallel(
                agent_dicts, shared_constraints, session=session))

        return "Task delegated to specialist agents. They are processing now. Provide a brief natural acknowledgment to the user."

    _tool.name = "delegate_to_agents"
    return _tool


async def _run_parallel(agents: list[dict], shared_constraints: str, session: dict | None = {}) -> str:

    business_id = session.get("business_id", "")
    emit_event = session.get("emit_event")
    vc_session = session.get("vc_session")

    async def run_one(agent_info: dict) -> str:
        agent_id = agent_info.get("agent_id", "")
        message_input = agent_info.get("message_input", "")

        agent = registry.get(agent_id)
        if agent is None:
            return f"Unknown agent: {agent_id}"

        try:
            task = f"{message_input}\n{shared_constraints}".strip()
            await agent.bind_tools(business_id, scopes=[])
            result = await agent.execute_agent(task)
            return result
        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {e}")
            return f"Error from {agent_id}: {str(e)}"

    tasks = [run_one(a) for a in agents]
    results = await asyncio.gather(*tasks)
    agent_response = "\n\n".join(r for r in results if r)

    if emit_event and agent_response:
        await emit_event("message", {
            "type": "message",
            "data": {"response": agent_response, "msg_type": "answer"},
        })

    if vc_session and agent_response:
        await vc_session.say(agent_response, allow_interruptions=True)

    return agent_response


async def _run_sequential(agents: list[dict], shared_constraints: str, session: dict | None = {}) -> str:

    business_id = session.get("business_id", "")
    emit_event = session.get("emit_event")
    vc_session = session.get("vc_session")

    results = []
    for agent_info in agents:
        agent_id = agent_info.get("agent_id", "")
        message_input = agent_info.get("message_input", "")

        agent = registry.get(agent_id)
        if agent is None:
            results.append(f"Unknown agent: {agent_id}")
            continue

        try:
            task = f"{message_input}\n{shared_constraints}".strip()
            agent.bind_tools(business_id, scopes=[])
            result = await agent.execute_agent(task)
            results.append(result)
        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {e}")
            results.append(f"Error from {agent_id}: {str(e)}")

    agent_response = "\n\n".join(r for r in results if r)

    if emit_event and agent_response:
        await emit_event("message", {
            "type": "message",
            "data": {"response": agent_response, "msg_type": "answer"},
        })

    if vc_session and agent_response:
        await vc_session.say(agent_response, allow_interruptions=True)

    return agent_response


class Planner:

    def __init__(self, session: dict = {}) -> None:
        self._session = session
        self._session_id = self._session.get("session_id", "")
        self._business_id = self._session.get("business_id", "")
        self._record_id = self._session.get("record_id", "")

        self._memory = Memory(
            scopes=[f"/conversations/{self._session_id}"],
            business_id=self._business_id,
            table_name="conversations",
        )
        manifests = self._load_manifests()

        system_context = (
            f"{manifests['agents']}\n\n"
            # f"{manifests['skills']}\n\n"
            # f"{manifests['knowledge']}\n\n"
            # f"{manifests['tools']}\n\n"
        )

        # self._runtime = AgentRuntime(
        #     tool_binder=ToolBinder(),
        #     agent=agent_spec,
        #     tools=[delegate_to_agents(session)],
        #     # allowed_input_guardrail=True,
        #     system_prompt=system_context,
        # )

        agent = Agent(
            name="Assistant",

            llm=llm,

            instructions="""
                You are a helpful assistant.

                Always use tools when appropriate.
                """,

            tools=[
                get_weather
            ],

            middleware=[
                ToolLoggingMiddleware(),
            ],
        )
        self._session = agent.create_session()

    async def _save_msg(self, messages: list[dict]):
        await save_messages(self._business_id, self._session_id, messages, record_id=self._record_id)

    async def run(self, user_message: str, conversation_history: list[dict] = [], messages: list | None = None):

        response = await self._session.run(
            "What's the weather in Lagos?"
        )

        print(response.text)
        for message in self._session.messages:
            print(message.content)

        # try:
        #     recent = await self._memory.fetch(limit=10)
        #     for r in recent:
        #         meta = r.metadata or {}
        #         conversation_history.append(
        #             {"role": meta.get("role", "user"), "content": r.content})
        # except Exception as e:
        #     logger.warning("Conversation msg history failed: %s", e)

        # if user_message.strip():
        #     await self._save_msg(messages=[{"role": "user", "content": user_message}])

        # response = await self._runtime.execute(
        #     user_message,
        #     chat_history=conversation_history,
        #     use_plan_mode=True,
        #     messages=messages,
        # )

        # try:
        #     await self._memory.save(content=user_message, metadata={"role": "user", "session_id": self._session_id})
        #     await self._memory.save(content=response, metadata={"role": "assistant", "session_id": self._session_id})
        # except Exception as e:
        #     logger.warning("Conversation history persist failed: %s", e)

        # await self._save_msg(messages=[{"role": "assistant", "content": response}])
        # return response

    def _load_manifests(self) -> dict[str, str]:
        manifest_names = ["agents", "skills", "tools", "knowledge"]
        manifests: dict[str, str] = {}
        for name in manifest_names:
            try:
                manifests[name] = load_manifest(name)
            except FileNotFoundError:
                raise PlanningError(
                    f"Manifest '{name}' is unreachable.", manifest=name)
        return manifests
