
from __future__ import annotations

from typing import Any

from app.llm.client import get_client
from app.runtime.utils.tag_parser import extract_tag

from .interface import (
    PresenceAction,
    PresencePhase,
    PresenceResult,
)
from .state import PresenceState


class PresenceLLM:

    def __init__(
        self,
        llm: Any | None = None,
        classifier_llm: Any | None = None,
        *,
        max_tokens: int = 160,
        classifier_max_tokens: int = 160,
    ) -> None:
        self._llm = (
            llm
            if llm is not None
            else get_client(
                config={
                    "max_token": max_tokens,
                },
            )
        )

        self._classifier_llm = (
            classifier_llm
            if classifier_llm is not None
            else get_client(
                config={
                    "max_token": classifier_max_tokens,
                },
            )
        )

        self._max_tokens = max_tokens
        self._classifier_max_tokens = classifier_max_tokens

    @property
    def max_tokens(
        self,
    ) -> int:
        return self._max_tokens

    @property
    def classifier_max_tokens(
        self,
    ) -> int:
        return self._classifier_max_tokens

    async def generate(
        self,
        *,
        state: PresenceState,
        phase: PresencePhase,
    ) -> PresenceResult:

        if phase is PresencePhase.INITIAL:
            response = await self._classifier_llm.ainvoke(
                self._build_initial_prompt(
                    state,
                ),
            )
            print('chekcing >>>', response)

        elif phase is PresencePhase.PROGRESS:
            response = await self._llm.ainvoke(
                self._build_progress_prompt(
                    state,
                ),
            )

        else:
            return PresenceResult(
                action=PresenceAction.HANDOFF,
            )

        content = self._extract_content(
            response,
        )

        if not content:
            if phase is PresencePhase.INITIAL:
                return PresenceResult(
                    action=PresenceAction.HANDOFF,
                )

            return PresenceResult(
                action=PresenceAction.STATUS,
            )

        if phase is PresencePhase.INITIAL:
            return self._parse_initial_response(
                content,
            )

        message = extract_tag(
            content,
            "message",
        )

        if not message:
            return PresenceResult(
                action=PresenceAction.STATUS,
            )

        message = message.strip()

        if not message:
            return PresenceResult(
                action=PresenceAction.STATUS,
            )

        return PresenceResult(
            action=PresenceAction.STATUS,
            message=message,
        )

    def _build_initial_prompt(
        self,
        state: PresenceState,
    ) -> str:
        return f"""
        You are a routing layer for the Tendo system. You must classify the user's message and execute exactly one action.

        CRITICAL LOGIC RULES:
        1. RESPOND: Select this action exclusively when the user's message is a non-transactional social exchange, greeting, small talk, or empty conversational acknowledgment. Do not hand off to the main agent. You must resolve the response dynamically at this layer.
        2. HANDOFF: Select this action immediately if the user's message requires data retrieval, information processing, computation, task execution, problem-solving, or system action. You must resolve the response dynamically at this layer.

        CRITICAL GENERATION RULES:
        - You must dynamically compose an original, context-appropriate message for BOTH RESPOND and HANDOFF.
        - The <message> must be appropriate for the selected action.
        - Do not use, copy, or reference any placeholder text, instructions, or template words from this system prompt in your output.
        - Generate an organic, human-to-human statement.
        - Absolute Prohibition: Do not repeat or echo the user's input phrase.
        - Absolute Prohibition: Do not expose private reasoning or internal system information.

        RESPOND MESSAGE RULES:
        - Keep the response brief, casual, and natural.
        - Do not state that the system is looking up information, initiating tasks, or working on a request.
        - Do not offer assistance.

        HANDOFF MESSAGE RULES:
        - Keep the message brief and natural.
        - The message should acknowledge the user's request naturally while the request is handed off.
        - Do not solve the user's request.
        - Do not provide the answer to the user's request.
        - Do not claim that a specific tool, search, agent, or backend operation has already started.
        - Do not expose internal reasoning or implementation details.
        - Do not repeat the user's request.
        - The message must still be useful as a natural spoken transition.

        OUTPUT FORMAT RULES (STRICT):
        - You must output valid XML structure only.
        - Do not append or prepend any text, markdown notation, backticks, or meta-commentary outside the XML boundaries.
        - You MUST always include exactly one <action> tag.
        - You MUST always include exactly one <message> tag.
        - The <action> must be either RESPOND or HANDOFF.
        - The <message> must contain the dynamically generated response.

        If RESPOND:
        <action>RESPOND</action>
        <message>[CONVERSATIONAL_RESPONSE]</message>

        If HANDOFF:
        <action>HANDOFF</action>
        <message>[HANDOFF_RESPONSE]</message>

        User message to classify:
        {state.user_request}
        """.strip()

    def _build_progress_prompt(
        self,
        state: PresenceState,
    ) -> str:
        completed_steps = ""

        if state.completed_steps:
            completed_steps = "\n".join(
                f"- {step}"
                for step in state.completed_steps[-5:]
            )

        return f"""
        You are the authoritative progress routing layer for the Tendo system. Your sole function is to generate a direct, brief status update while the background engine processes a task.

        CRITICAL LOGIC RULES:
        - You must generate exactly  short sentences optimized for immediate, direct delivery.
        - Base your update exclusively on the provided runtime state data. Do not extrapolate, infer, or assume any progress that is not explicitly stated.
        - Do not greet the user, acknowledge anything unrelated to the immediate progress, or repeat the user's request.
        - Do not solve the request, provide final answers, or expose internal processing details.

        ABSOLUTE PROHIBITIONS:
        - No Self-Reference: Do not mention, imply, or reference any entity, agent, actor, platform, or identity executing the task.
        - No Internal State Meta-Commentary: Do not describe any cognitive, computational, or analytical activities. Focus entirely on the objective, external data results provided in the state.
        - No Passive Stalling: Do not use structural time-wasting, waiting, or filler phrases.
        - No Styling: Do not include markdown, bullets, text symbols, or emojis. Output plain prose only.
        - No Template Copying: Do not use, copy, or reference any placeholder text, instructions, or template words from this system prompt in your final output message.

        CURRENT STATE DATA:
        User request: {state.user_request}
        Current status: {state.status}
        Current progress: {state.message}
        Completed steps: {completed_steps or "None"}

        OUTPUT FORMAT RULES (STRICT):
        - You must output valid XML structure only. 
        - Do not add any conversational preamble, intro text, markdown wrappers, or backticks outside the XML boundaries.

        <message>[STATUS_PROGRESS_REPLY]</message>

        """.strip()

    @staticmethod
    def _parse_initial_response(
        content: str,
    ) -> PresenceResult:

        action = extract_tag(
            content,
            "action",
        )

        if not action:
            return PresenceResult(
                action=PresenceAction.HANDOFF,
            )

        action = action.strip().upper()

        message = extract_tag(
            content,
            "message",
        )

        if message:
            message = message.strip()

        if action == PresenceAction.RESPOND.value.upper():
            if not message:
                return PresenceResult(
                    action=PresenceAction.HANDOFF,
                )

            return PresenceResult(
                action=PresenceAction.RESPOND,
                message=message,
            )

        if action == PresenceAction.HANDOFF.value.upper():
            return PresenceResult(
                action=PresenceAction.HANDOFF,
                message=message or None,
            )

        return PresenceResult(
            action=PresenceAction.HANDOFF,
            message=message or None,
        )

    @staticmethod
    def _extract_content(
        response: Any,
    ) -> str | None:

        if response is None:
            return None

        content = getattr(
            response,
            "content",
            None,
        )

        if content is None:
            return None

        if isinstance(content, str):
            return content.strip() or None

        if isinstance(content, list):
            parts: list[str] = []

            for item in content:
                if isinstance(item, str):
                    parts.append(item)

                elif isinstance(item, dict):
                    text = item.get("text")

                    if isinstance(text, str):
                        parts.append(text)

            result = "".join(parts).strip()

            return result or None

        return str(content).strip() or None
