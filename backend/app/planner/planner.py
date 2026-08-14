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
from app.runtime.middlewares.middleware import AgentMiddleware
from app.runtime.toolsets.executor import ToolExecutionResult
from app.runtime.toolsets import function_tool
from app.llm.client import get_client
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.memory.factory import (
    create_memory_provider,
)
from app.runtime.rag.factory import (
    create_rag_provider
)

from app.runtime.conversation.factory import (
    create_conversation_provider
)
from app.runtime.utils.spec_loader import LoaderAgentSpec
from app.runtime.events.default_emitter import DefaultEmitter
from app.runtime.events.events import (EventType, StatusEvent)


specialist_info = {
    "planner": LoaderAgentSpec.from_spec(name='Planner Specialist', path='planner'),
    "knowledge": LoaderAgentSpec.from_spec(name='Knowledge  Specialist', path='domain/knowledge'),
    "transaction": LoaderAgentSpec.from_spec(name='Transactions  Specialist', path='domain/transactions'),
    "inventory": LoaderAgentSpec.from_spec(name='Inventory  Specialist', path='domain/inventory'),
}


planner_system_prompt = (
    f"Role:\n{specialist_info.get('planner').role}\n\n"
    f"Backstory:\n{specialist_info.get('planner').backstory}\n\n"
    f"Goal:\n{specialist_info.get('planner').goal}\n\n"
    "Other Specialized Business Employees:\n\n"
    "## transaction\n"
    "- **Domain**: transaction\n"
    "- **Capabilities**: search, query, update, add\n"
    "- **Description**: It is only used for business transaction recording and financial queries.\n\n"
    "## inventory\n"
    "- **Domain**: inventory\n"
    "- **Capabilities**: search, query, update, track, and manage\n"
    "- **Description**: It is only used for managing inventory and tracking.\n\n"
    "## knowledge\n"
    "- **Domain**: knowledge\n"
    "- **Capabilities**: search, retrieve\n"
    "- **Description**: It is used to answer general questions of all types as the source of truth.\n\n"
)


emitter = DefaultEmitter()

_llm_instance = None


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LangChainLLM(model=get_client())
    return _llm_instance


logger = logging.getLogger(__name__)

try:
    from app.agents.models import Agent as AgentModel
    agent_spec = AgentModel.from_spec("planner")
except Exception:
    agent_spec = None


@tool
async def get_weather(
    city: str,
) -> str:
    """
    Get the weather for a city.
    """

    return f"{city}: Sunny"


@tool
async def get_temperature(
    city: str,
) -> str:
    """
    Get the temperature of city.
    """

    return f"{city}: 50°C "


class ToolLoggingMiddleware(AgentMiddleware):
    """Logs tool calls and their results."""

    async def before_tools(self, ctx, event) -> None:

        logger.info("[middleware] Tool execution starting...")
        # print(event.tool_calls)
        # print('\n\n')

    async def after_tools(self, ctx, event) -> None:
        for r in event.results:
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
        """This tool is used to delegate task to other specialist for further task processing 
           Args:
              specialists: List of agent assignments. Each must have:
                - specialist_id: <agent_name>
                - message_input: <user_message>
                - depends_on: List of specialist_ids this specialist depends on
              shared_constraints: Constraints that apply to all specialists.

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
        print("we ar here ......")
        return "Task delegated to specialist agents. They are processing now. Provide a brief natural acknowledgment to the user."

    _tool.name = "discover_information"
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


async def _run_sequential(specialists: list[dict], shared_constraints: str, session: dict | None = {}) -> str:
    results = []
    try:
        business_id = session.get("business_id", "")
        session_id = session.get('session_id', "")
        record_id = session.get('record_id', '')
        emit_event = session.get("emit_event")
        vc_session = session.get("vc_session")

        for specialist in specialists:
            selected_specailist_id = specialist.get("agent_id", "")
            specialist_spec = specialist_info.get(selected_specailist_id, "")
            message_input = agent_info.get("message_input", "")

            if specialist_spec:
                results.append(
                    f"Delegated specialist not found for : {agent_id}")
                continue

            scopes = [f"business/{business_id}",
                      f"business/{business_id}/record/{record_id}"]

            system_prompt = (
                f"Role:\n{specialist_spec.get(selected_specailist_id).role}\n\n"
                f"Backstory:\n{specialist_spec.get(selected_specailist_id).backstory}\n\n"
                f"Goal:\n{specialist_spec.get(selected_specailist_id).goal}\n\n"
            )

            agent = Agent(
                name=selected_specailist_id,
                llm=_get_llm(),
                memory=create_memory_provider(
                    namespace=business_id, scopes=scopes),
                rag=create_rag_provider(namespace=business_id, scopes=scopes),
                conversation=create_conversation_provider(
                    namespace=business_id),
                instructions=system_prompt,

                tools=[

                ],
            )

            _session = agent.create_session(
                session_id=session_id,
                emitter=emitter,
            )

            response = await _session.run(
                user_message
            )

            results.append(response.text)

        all_response = "\n\n".join(r for r in results if r)

        if emit_event and agent_response:
            await emit_event("message", {
                "type": "message",
                "data": {"response": all_response, "msg_type": "answer"},
            })

        if vc_session and agent_response:
            await vc_session.say(all_response, allow_interruptions=True)

        return all_response
    except Exception as e:
        logger.error(f"Paralles execution failed: {e}")
        print(e)


class Planner:

    def __init__(self, session: dict = {}, callbacks: list[Any] | None = []) -> None:
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

        emitter.on(EventType.PROGRESS, callbacks)

        agent = Agent(
            name="Assistant",

            llm=_get_llm(),
            memory=create_memory_provider(namespace=self._business_id),
            rag=create_rag_provider(namespace=self._business_id),
            conversation=create_conversation_provider(
                namespace=self._business_id),
            instructions=planner_system_prompt,

            tools=[
                get_temperature,
                get_weather,
                delegate_to_agents(session)
            ],

            middleware=[
                ToolLoggingMiddleware(),
            ],
        )
        self._session = agent.create_session(
            session_id=self._session_id,
            emitter=emitter,
        )

    async def _save_msg(self, messages: list[dict]):
        await save_messages(self._business_id, self._session_id, messages, record_id=self._record_id)

    async def run(self, user_message: str, conversation_history: list[dict] = [], messages: list | None = None):

        response = await self._session.run(
            user_message
        )

        print(response.text)
        # print(self._session.run_context.messages)
        # for message in self._session.run_context.messages:
        #     print(message)

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
        return response.text

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
