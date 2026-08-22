from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.llm.client import get_client
from app.runtime.agents.agent import Agent
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.utils.tag_parser import (
    extract_json,
    extract_tag,
)
from app.runtime.utils.spec_loader import LoaderAgentSpec

from .models import (
    SnapModel,
    SnapPriority,
    SnapType
)
from app.runtime.utils.pydantic import pydantic_to_string
from app.runtime.memory.factory import create_memory_provider

logger = logging.getLogger(__name__)

_llm_instance: LangChainLLM | None = None


_MAX_ATTEMPTS = 3

_SNAP_TAG = "signal"

_MAX_TITLE_LENGTH = 80
_MAX_MESSAGE_LENGTH = 240
_MAX_WHY_IT_MATTERS_LENGTH = 180
_MAX_ACTION_LENGTH = 160


class SnapOutput(BaseModel):
    """
    Strict schema for Snap objects.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    type: SnapType = Field(
        description=(
            "The category of the Snap. "
            "Use recommendation for a suggested action, "
            "attention for something that deserves review, "
            "warning for a potential risk or problem, "
            "opportunity for a potentially valuable development"
        ),
    )

    priority: SnapPriority = Field(
        description=(
            "The urgency or importance of the Snap. "
            "Use low for minor items, medium for items worth "
            "attention, high for important items requiring timely "
            "action, and critical for matters requiring immediate "
            "attention."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Confidence that the Snap is meaningful and supported "
            "by the available information. A value between 0.0 "
            "and 1.0, where 1.0 represents very high confidence."
        ),
    )

    title: str = Field(
        min_length=1,
        max_length=_MAX_TITLE_LENGTH,
        description=(
            "A concise title that summarizes the key signal. "
            "Maximum 80 characters."
        ),
    )

    message: str = Field(
        min_length=1,
        max_length=_MAX_MESSAGE_LENGTH,
        description=(
            "A concise explanation of what was observed or "
            "identified. It should communicate the important "
            "signal without unnecessary detail. Maximum "
            "240 characters."
        ),
    )

    why_it_matters: str = Field(
        min_length=1,
        max_length=_MAX_WHY_IT_MATTERS_LENGTH,
        description=(
            "A concise explanation of why the signal is important "
            "or why the user should care about it. Maximum "
            "180 characters."
        ),
    )

    action: str = Field(
        min_length=1,
        max_length=_MAX_ACTION_LENGTH,
        description=(
            "A concise recommended next step or action the user "
            "can take in response to the Snap. Maximum "
            "160 characters."
        ),
    )


SnapOutputList = TypeAdapter(
    list[SnapOutput],
)


def _get_llm() -> LangChainLLM:

    global _llm_instance

    if _llm_instance is None:
        _llm_instance = LangChainLLM(
            model=get_client(),
        )

    return _llm_instance


spec = LoaderAgentSpec.from_spec(
    name="Snap Specialist",
    path="snapshot",
)


system_prompt = (
    f"{spec.backstory}\n\n"
    f"{spec.role}\n\n"
    f"{spec.goal}\n\n"
    "The runtime context available to you is the only basis "
    "for generating Signals from 5-10 signals.\n\n"
    "Do not ask for additional information.\n"
    "Do not generate a Signals about missing context.\n"
    "Do not generate a generic or hypothetical Signals.\n"
    f"Return only the JSON array of signal objects inside the "
    f"<{_SNAP_TAG}>...</{_SNAP_TAG}> tag.\n"
    f"If no meaningful signal is supported, return "
    f"<{_SNAP_TAG}>[]</{_SNAP_TAG}>.\n\n"
    "Every field is length limited. A response that exceeds any "
    "limit is rejected, so keep each field within its budget:\n"
    f"- title: at most {_MAX_TITLE_LENGTH} characters\n"
    f"- message: at most {_MAX_MESSAGE_LENGTH} characters\n"
    f"- why_it_matters: at most {_MAX_WHY_IT_MATTERS_LENGTH} characters\n"
    f"- action: at most {_MAX_ACTION_LENGTH} characters\n\n"
    "<Output Format>:\n\n"
    f"<{_SNAP_TAG}>\n"
    f"{pydantic_to_string(SnapOutputList)}\n"
    f"</{_SNAP_TAG}>\n\n"
)


trigger_prompt = (
    "Review all available information and identify any meaningful "
    "findings worth surfacing. Consider each relevant piece of "
    "information and their relationships.\n\n"
)


class SnapAgent:

    def __init__(
        self,
        namespace: str,
        scopes: list[str] = [],
    ) -> None:

        self._agent = Agent(
            name="SNAP",
            llm=_get_llm(),
            instructions=system_prompt,
            memory=create_memory_provider(
                namespace=namespace,
                scopes=scopes,
                ignore_threshold=True
            ),
            enable_self_reflection=False,
            enable_runtime_rag=False,
            enable_runtime_mem=True,
            max_iteration=4,
            max_reasoning_steps=2
        )

    @property
    def agent(self) -> Agent:

        return self._agent

    async def generate(
        self,
        *,
        business_id: str,
        existing_snaps: list[dict[str, Any]],
    ) -> list[SnapModel]:

        print('existing signals', existing_snaps)

        business_id = business_id.strip()

        if not business_id:
            raise ValueError(
                "business_id cannot be empty.",
            )

        session = self._agent.create_session()

        prompt = trigger_prompt

        last_error: ValueError | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):

            response = await session.run(
                prompt,
            )

            print(response)

            try:

                return self._parse_response(
                    response=response.text,
                )

            except ValueError as exc:

                last_error = exc

                logger.warning(
                    "Snap Agent response rejected "
                    "(attempt %s/%s) for business %s: %s",
                    attempt,
                    _MAX_ATTEMPTS,
                    business_id,
                    exc,
                )

                prompt = self._build_retry_prompt(
                    error=exc,
                    attempt=attempt,
                )

        logger.error(
            "Snap Agent produced no valid signals after "
            "%s attempts for business %s: %s",
            _MAX_ATTEMPTS,
            business_id,
            last_error,
        )

        return []

    @staticmethod
    def _build_retry_prompt(
        *,
        error: ValueError | None,
        attempt: int,
    ) -> str:

        error_message = (
            str(error)
            if error
            else "Unknown validation error."
        )

        return (
            "Your previous response could not be accepted "
            "as a valid signals response.\n\n"
            f"Validation error:\n{error_message}\n\n"
            f"This is retry attempt {attempt} of "
            f"{_MAX_ATTEMPTS}.\n\n"
            "Respect every maxLength constraint. If a message does "
            "not fit, split it into separate signals or shorten it.\n\n"
            "Correct the response and return ONLY this structure "
            f"inside the <{_SNAP_TAG}>...</{_SNAP_TAG}> tag:\n\n"
            f"{pydantic_to_string(SnapOutputList)}\n\n"
        )

    @staticmethod
    def _parse_response(
        response: str,
    ) -> list[SnapModel]:

        raw = extract_tag(
            response,
            _SNAP_TAG,
        )

        if not raw:

            raise ValueError(
                "Snap Agent response is missing "
                f"the <{_SNAP_TAG}> tag.",
            )

        payload = extract_json(
            raw,
        )

        if payload is None:

            raise ValueError(
                "Snap Agent returned invalid JSON "
                f"inside the <{_SNAP_TAG}> tag.",
            )

        try:

            outputs = SnapOutputList.validate_python(
                payload,
            )

        except Exception as exc:

            raise ValueError(
                "Snap Agent returned a response that "
                "does not match the Snap schema: "
                f"{exc}",
            ) from exc

        return [
            SnapAgent._to_model(
                output,
            )
            for output in outputs
        ]

    @staticmethod
    def _to_model(
        output: SnapOutput,
    ) -> SnapModel:

        return SnapModel(
            type=output.type,
            priority=output.priority,
            confidence=output.confidence,
            title=output.title.strip(),
            message=output.message.strip(),
            why_it_matters=output.why_it_matters.strip(),
            action=output.action.strip(),
        )
