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
    SnapType,
    SnapDomain
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
_MAX_DOMAIN_LENGTH = 30


class SnapOutput(BaseModel):
    """
    Strict schema for user-relevant Signal objects.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    type: SnapType = Field(
        description=(
            "The kind of signal being surfaced. "
            "Use recommendation for a useful suggested action, "
            "attention for information the user should notice or review, "
            "warning for a potential risk, problem, or anomaly, "
            "or opportunity for a potentially valuable development."
        ),
    )

    domain: SnapDomain = Field(
        description=(
            "The  domain that the Signal belongs to. "
            "Use the most specific domain supported by the available "
            "information. Do not invent a domain that is "
            "not supported by the Signal."
        ),
    )

    priority: SnapPriority = Field(
        description=(
            "How important the signal is relative to the user's "
            "configured interests and preferences. "
            "Use low for minor relevance, medium for meaningful "
            "relevance, high for important or time-sensitive signals, "
            "and critical for matters requiring immediate attention."
        ),
    )

    confidence: float = Field(
        description=(
            "Confidence that the signal is both supported by the "
            "available information and relevant to the user's "
            "configured preferences. 1.0 means very high confidence."
        ),
    )

    title: str = Field(
        description=(
            "A concise title describing the specific signal that "
            "matches the user's configured preferences. "
            "Maximum 80 characters."
        ),
    )

    message: str = Field(
        description=(
            "A concise description of the relevant information "
            "identified in the available context. State what was "
            "observed and why it matches the user's interests or "
            "configured preferences. Maximum 240 characters."
        ),
    )

    why_it_matters: str = Field(
        description=(
            "A concise explanation of why this information matters "
            "to the user specifically, based on their configured "
            "preferences or notification criteria. Maximum 180 "
            "characters."
        ),
    )

    action: str = Field(
        description=(
            "A concise, evidence-based next step when one is "
            "reasonably useful. Do not invent an action merely to "
            "complete the field. Maximum 160 characters."
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

    "Ignore information that does not match the user's "
    "configured preferences.\n"

    "Do not summarize information simply because it is present.\n"

    "Do not invent findings, causes, implications, or "
    "recommendations that are not supported by the available "
    "information.\n"

    "Do not ask for additional information.\n"

    "Generate a separate Signal for each materially distinct "
    "finding that matches the user's preferences.\n"

    "Do not use the existing signal content for query or reterival.\n"
    "Existing signal is given to you to avoid regenerating signal that currently exist.\n"
    "If signal already exist do not generate. Insteady exclude from generated signals\n"

    f"Do not add any tag except <{_SNAP_TAG}>.\n"

    f"Return only the JSON array of Signal objects inside "
    f"the <{_SNAP_TAG}>...</{_SNAP_TAG}> tag.\n"

    f"If no meaningful Signal is supported, return "
    f"<{_SNAP_TAG}>[]</{_SNAP_TAG}>.\n\n"

    "Every field is length limited. A response that exceeds "
    "any limit is rejected. Keep each field within its budget:\n"

    f"- title: at most {_MAX_TITLE_LENGTH} characters\n"
    f"- message: at most {_MAX_MESSAGE_LENGTH} characters\n"
    f"- why_it_matters: at most {_MAX_WHY_IT_MATTERS_LENGTH} characters\n"
    f"- action: at most {_MAX_ACTION_LENGTH} characters\n\n"
    f"- confidence: at range of 0.0 to 1.0\n\n"
    f"- domain: at most {_MAX_DOMAIN_LENGTH} characters\n\n"

    "<Existing Signals>:\n{existing_signals}\n"
    "<Output Format>\n"
    f"<{_SNAP_TAG}>\n"
    f"{pydantic_to_string(SnapOutputList)}\n"
    f"</{_SNAP_TAG}>\n"
)

preferences = """
Documents, Story, business growth, operational problems, delays, unusual activity,
recurring issues, important changes in performance, and situations that
may require intervention.
"""

trigger_prompt = (
    "Evaluate the available information against the preferred Signals and "
    "generate signals from those informatin that needs attentions. "
    "A Signal is a specific finding in the available information that matches "
    "one or more of the user's preferred Signal types and is supported by evidence.\n\n"
    "Create a separate Signal for each materially distinct finding.\n"
    f"<Preferred Signals>:\n{preferences}\n\n"
)


class SnapAgent:

    def __init__(
        self,
        namespace: str,
        scopes: list[str] = [],
    ) -> None:
        self._agent: Agent
        self._llm = _get_llm()
        self._mem = create_memory_provider(
            namespace=namespace,
            scopes=scopes,
            ignore_threshold=True
        )

    @property
    def agent(self) -> Agent:

        return self._agent

    def _format_snaps(self, snaps: list[dict[str, Any]]) -> str:

        lines = []
        for snap in snaps:
            _snap = (
                f"type:{snap.get('type')}\n"
                f"title:{snap.get('title')}\n"
                f"message:{snap.get('message')}\n"
                f"why_it_matters:{snap.get('why_it_matters')}\n"
                f"action:{snap.get('action')}\n"
                f"domain:{snap.get('domain')}\n"
            )
            lines.append(_snap)

        return '\n'.join(lines)

    async def generate(
        self,
        *,
        business_id: str,
        existing_snaps: list[dict[str, Any]],
    ) -> list[SnapModel]:

        business_id = business_id.strip()

        if not business_id:
            raise ValueError(
                "business_id cannot be empty.",
            )

        self._agent = Agent(
            name="SNAP",
            llm=self._llm,
            instructions=system_prompt
            .replace("{existing_signals}", self._format_snaps(snaps=existing_snaps)),
            memory=self._mem,
            enable_self_reflection=False,
            enable_runtime_rag=False,
            enable_runtime_mem=True,
            max_iteration=4,
            max_reasoning_steps=2
        )

        session = self._agent.create_session()

        prompt = trigger_prompt

        last_error: ValueError | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):

            response = await session.run(
                prompt,
            )

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
            domain=output.domain.strip()
        )
