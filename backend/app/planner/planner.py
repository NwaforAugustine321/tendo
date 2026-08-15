from __future__ import annotations

import asyncio
import logging
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
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
from app.runtime.events.events import (EventType, StatusEvent)
from app.runtime.conversation.factory import (
    create_conversation_provider
)
from app.runtime.utils.spec_loader import LoaderAgentSpec
from app.runtime.events.default_emitter import DefaultEmitter
from app.runtime.events.emit_forwarder import EmitForwarder


specialist_info = {
    "planner": LoaderAgentSpec.from_spec(name='Planner Specialist', path='planner'),
    "knowledge": LoaderAgentSpec.from_spec(name='Knowledge  Specialist', path='domain/knowledge'),
    "transaction": LoaderAgentSpec.from_spec(name='Transactions  Specialist', path='domain/transactions'),
    "inventory": LoaderAgentSpec.from_spec(name='Inventory  Specialist', path='domain/inventory'),
}


planner_system_prompt = (
    f"{specialist_info.get('planner').backstory}\n\n"
    f"{specialist_info.get('planner').role}.\n\n"
    f"{specialist_info.get('planner').goal}\n\n"
    "Other Specialized Business Employees (You are not allowed to expose the name and how internal working of these bussines employees works with you):\n\n"
    "## transaction\n"
    "## inventory\n"
    "## knowledge\n"
)


def _create_emitter(emit_event=None):

    forwarder = EmitForwarder(emit_fn=emit_event)
    emitter = DefaultEmitter()

    async def progress_callback(event: StatusEvent):
        await forwarder.emit("progress", {
            "status": event.status.value,
            "message": event.message,
        })

    emitter.on(EventType.PROGRESS, [progress_callback])
    return emitter


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
        print(event.tool_calls)
        print('\n\n')

    async def after_tools(self, ctx, event) -> None:
        for r in event.results:
            logger.info(
                "tool result"
            )
            print(r.output)
            print('\n')


class SelectedSpecialist(BaseModel):
    specialist_id: str = Field(
        default_factory=str, description="Specialist Id.")
    depends_on: list = Field(
        default_factory=list[str], description="List of specialist_id the agent depend on")
    message_input: str = Field(..., min_length=1,
                               description="Clear instruction for what the specialist must accomplish")


class SpecialistSelectionOutput(BaseModel):
    specialists: list[SelectedSpecialist] = Field(
        default_factory=list, description="List of specialists to handle the request. Each has specialist_id, execution_context, and depends_on.")
    shared_constraints: str = Field(
        default_factory=str, description="Shared constraints for all specialists execution")


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
        specialists: list[SelectedSpecialist],
        shared_constraints: str = "",
    ) -> str:
        """
        Delegate work to one or more business specialists.

        Use this tool when the task requires business information,
        domain expertise, knowledge retrieve search, data, actions, search, retrieve, knowledge, answer and others or capabilities handled by
        one or more specialists.

        Args:
            specialists: Specialist assignments. Each assignment contains:
                - specialist_id: Identifier of the specialist to handle the task.
                - message_input: Specific task or information request for the specialist.
                - depends_on: Specialist IDs whose results are required before
                this specialist can proceed. Use an empty list when independent.

            shared_constraints: Constraints, requirements, or instructions that
                apply to all assigned specialists.

        Returns:
            A string containing the specialists' results and execution outcome.
        """

        has_dependencies = any(
            len(a.depends_on) > 0 for a in specialists if hasattr(a, 'depends_on')
        )

        specialist_dicts = [a.model_dump() if hasattr(
            a, 'model_dump') else a for a in specialists]

        if has_dependencies:
            asyncio.create_task(_run_sequential(
                specialist_dicts, shared_constraints, session=session))
        else:
            asyncio.create_task(_run_parallel(
                specialist_dicts, shared_constraints, session=session))

        return "Task delegated to specialists. They are processing now. Provide a brief natural acknowledgment to the user."

    _tool.name = "delegate_to_specailist"
    return _tool


async def _run_parallel(specialists: list[dict], shared_constraints: str, session: dict | None = {}) -> str:

    business_id = session.get("business_id", "")
    session_id = session.get('session_id', "")
    record_id = session.get('record_id', '')
    emit_event = session.get("emit_event")
    vc_session = session.get("vc_session")
    emitter = _create_emitter(emit_event)

    async def run_one(specialist: dict) -> str:
        print("running specialist >>>>>>>>>>>.: " + str(specialist))
        selected_specailist_id = specialist.get("specialist_id", "")
        specialist_spec = specialist_info.get(selected_specailist_id, "")
        message_input = specialist.get("message_input", "")

        if not specialist_spec:
            return f"Delegated specialist not found for: {selected_specailist_id}"

        scopes = [f"business/{business_id}",
                  f"business/{business_id}/record/{record_id}"]

        system_prompt = (
            f"Role:\n{specialist_spec.role}\n\n"
            f"Backstory:\n{specialist_spec.backstory}\n\n"
            f"Goal:\n{specialist_spec.goal}\n\n"
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

        try:
            _session = agent.create_session(
                session_id=session_id,
                emitter=emitter,
            )

            response = await _session.run(
                message_input
            )

            return response.text

        except Exception as e:
            logger.error(f"Agent {selected_specailist_id} failed: {e}")
            return f"Error from {selected_specailist_id}: {str(e)}"

    tasks = [run_one(a) for a in specialists]
    results = await asyncio.gather(*tasks)
    specialists_response = "\n\n".join(r for r in results if r)

    if emit_event and specialists_response:
        await emit_event("message", {
            "type": "message",
            "data": {"response": specialists_response, "msg_type": "answer"},
        })

    if vc_session and specialists_response:
        await vc_session.say(specialists_response, allow_interruptions=True)

    return specialists_response


async def _run_sequential(specialists: list[dict], shared_constraints: str, session: dict | None = {}) -> str:
    results = []
    try:
        business_id = session.get("business_id", "")
        session_id = session.get('session_id', "")
        record_id = session.get('record_id', '')
        emit_event = session.get("emit_event")
        vc_session = session.get("vc_session")
        emitter = _create_emitter(emit_event)

        for specialist in specialists:
            selected_specailist_id = specialist.get("specialist_id", "")
            specialist_spec = specialist_info.get(selected_specailist_id, "")
            message_input = specialist.get("message_input", "")

            if not specialist_spec:
                results.append(
                    f"Delegated specialist not found for: {selected_specailist_id}")
                continue

            scopes = [f"business/{business_id}",
                      f"business/{business_id}/record/{record_id}"]

            system_prompt = (
                f"Role:\n{specialist_spec.role}\n\n"
                f"Backstory:\n{specialist_spec.backstory}\n\n"
                f"Goal:\n{specialist_spec.goal}\n\n"
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
                message_input
            )

            results.append(response.text)

        all_response = "\n\n".join(r for r in results if r)

        if emit_event and all_response:
            await emit_event("message", {
                "type": "message",
                "data": {"response": all_response, "msg_type": "answer"},
            })

        if vc_session and all_response:
            await vc_session.say(all_response, allow_interruptions=True)

        return all_response
    except Exception as e:
        logger.error(f"Paralles execution failed: {e}")
        print(e)


class Planner:

    def __init__(self, session: dict = {}) -> None:
        self._session = session
        self._session_id = self._session.get("session_id", "")
        self._business_id = self._session.get("business_id", "")
        self._record_id = self._session.get("record_id", "")
        emit_event = self._session.get("emit_event")

        scopes = [f"business/{self._business_id}"]

        if self._record_id:
            scopes.append(
                f"business/{self._business_id}/record/{self._record_id}")

        emitter = _create_emitter(emit_event)

        agent = Agent(
            name="Assistant",

            llm=_get_llm(),
            memory=create_memory_provider(
                namespace=self._business_id, scopes=scopes),
            rag=create_rag_provider(
                namespace=self._business_id, scopes=scopes),
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

        return response.text
