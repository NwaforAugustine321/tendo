from __future__ import annotations

from typing import Any

from app.llm.client import get_client
from app.runtime.agents.agent import Agent
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.utils.spec_loader import LoaderAgentSpec

from .models import LearningResult
from .service import LearningService
from .memory import (
    LearningKnowledgeMemory,
)

_llm_instance: LangChainLLM | None = None


def _get_llm() -> LangChainLLM:

    global _llm_instance

    if _llm_instance is None:
        _llm_instance = LangChainLLM(
            model=get_client(),
        )

    return _llm_instance


spec = LoaderAgentSpec.from_spec(
    name="BLA Specialist",
    path="bla",
)


system_prompt = (
    f"{spec.backstory}\n\n"
    f"{spec.role}\n\n"
    f"{spec.goal}"
)


class BusinessLearningAgent:

    def __init__(
        self,
        namespace: str,
        scopes: list[str] = []
    ) -> None:

        knowledge_store = LearningKnowledgeMemory(
            namespace=namespace,
            scopes=scopes,
        )

        self._agent = Agent(
            name="BLA",
            llm=_get_llm(),
            instructions=system_prompt,
            tools=[],
            memory=knowledge_store,
            enable_self_reflection=False,
            enable_runtime_rag=False,
            enable_runtime_mem=True
        )

        self._learning_service = LearningService(knowledge=knowledge_store)

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def learning_service(self) -> LearningService:
        return self._learning_service

    async def learn(
        self,
        *,
        business_id: str,
        batch_size: int = 10
    ) -> LearningResult:

        business_id = business_id.strip()

        if not business_id:
            raise ValueError(
                "business_id cannot be empty.",
            )

        async def execute_learning(
            *,
            business_id: str,
            information: list[dict[str, Any]],
        ) -> LearningResult:

            return await self._run_agent(
                business_id=business_id,
                information=information,
            )

        return await self._learning_service.process(
            business_id=business_id,
            learn=execute_learning,
            batch_size=batch_size,
        )

    async def _run_agent(
        self,
        *,
        business_id: str,
        information: list[dict[str, Any]],
    ) -> LearningResult:

        session = self._agent.create_session()

        prompt = (
            "New information:\n"
            f"{information}\n\n"
            "Develop the updated durable knowledge by considering "
            "this information together with the existing knowledge "
            "available to you."
        )

        response = await session.run(
            prompt,
        )

        return LearningResult(
            knowledge=[response.text] if response.text else [],
        )
