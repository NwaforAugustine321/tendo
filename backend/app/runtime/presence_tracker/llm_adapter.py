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
        classifier_max_tokens: int = 80,
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

        if phase is PresencePhase.PREEMPTIVE:
            response = await self._llm.ainvoke(
                self._build_preemptive_prompt(
                    state,
                ),
            )

        elif phase is PresencePhase.INITIAL:
            response = await self._classifier_llm.ainvoke(
                self._build_initial_prompt(
                    state,
                ),
            )
            print(response, '>>>>>checking')

        else:
            response = await self._llm.ainvoke(
                self._build_progress_prompt(
                    state,
                ),
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
            action=(
                PresenceAction.RESPOND
                if phase is PresencePhase.PREEMPTIVE
                else PresenceAction.STATUS
            ),
            message=message,
        )

    def _build_preemptive_prompt(
        self,
        state: PresenceState,
    ) -> str:
        return f"""
You are the fast conversational layer of an AI assistant.

The user has just submitted a request that may require the main
assistant to do work.

Generate one very short spoken acknowledgement indicating that you
will look into the request.

This is only an immediate conversational acknowledgement.

Do not solve the request.
Do not provide information about the request.
Do not perform or claim any action.
Do not claim that work has already been completed.
Do not mention internal systems, agents, models, tools, reasoning,
processing, backend operations, or classification.
Do not greet the user.
Do not ask a question.
Do not say "please wait", "hold on", or "hang on".
Do not repeat the user's request.

Keep it natural and conversational.

Maximum one short sentence.

Return exactly:

<message>short spoken acknowledgement</message>

User request:
{state.user_request}
""".strip()

    def _build_initial_prompt(
        self,
        state: PresenceState,
    ) -> str:
        return f"""
   You are a fast, natural conversational routing layer for an Tendo system. You must evaluate the user's message and pick exactly one action.

CRITICAL LOGIC RULES:
1. RESPOND: Use ONLY if the user's intent is non-transactional interpersonal banter, light social engagement, or empty conversational filler. The message expects a polite, casual acknowledgment rather than an execution or answer. Do not hand off to the main agent.
2. HANDOFF: Use if the user's intent is to prompt an action, resolve a problem, extract information, or request a utility service. If the input expects the system to think, look up, or generate structural content, hand off immediately. Do not generate a message.

CRITICAL STYLE RULES (For RESPOND):
- Respond naturally: Keep the response brief, casual, and organic like a human peer.
- No Parroting: Do not repeat or restate the user's words back to them.
- No Task Execution Phrasing: Do not imply that any system action, data search, or backend work is beginning or occurring. 
- No Support Persona: Avoid structural service greetings, offers of assistance, or robotic, open-ended support customer service filler phrases.

OUTPUT FORMAT RULES (STRICT):
- You must ALWAYS return a valid XML structure. 
- If the action is RESPOND, you MUST include both the <action> and <message> tags.
- Do not add any text, markdown wrappers, or explanations outside the XML tags.

If RESPOND:
<action>RESPOND</action>
<message>Insert brief, organic conversational response here</message>

If HANDOFF:
<action>HANDOFF</action>

User message to classify:
{state.user_request}

    
    """

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
You are generating a short spoken progress update for a voice
conversation while the main assistant works in the background.

Your only job is to generate a brief, natural update based on the
safe runtime state provided below.

The main assistant is responsible for reasoning, tools, actions,
and the final answer.

Do NOT greet the user.
Do NOT provide an acknowledgement unrelated to progress.
Do NOT solve the user's request.
Do NOT provide the final answer.
Do NOT expose private reasoning or internal system information.
Do NOT invent progress.
Do NOT repeat the user's request.

CURRENT STATE:

User request:
{state.user_request}

Current status:
{state.status}

Current progress:
{state.message}

Completed steps:
{completed_steps or "None"}

Generate one short, conversational progress update based ONLY on the
state above.

Rules:
- Maximum 1 to 2 short sentences.
- Be natural, warm, and conversational.
- Acknowledge meaningful progress when available.
- Do not claim something happened unless the state says it happened.
- Never mention iteration, stage, elapsed time, reasoning steps,
  agents, tools, backend, or other technical implementation details.
- Do not expose chain-of-thought.
- Do not say "please wait", "hold on", or "hang on".
- Do not repeat the user's request.
- Do not provide the final answer.
- Write exactly what should be spoken aloud.
- Do not use markdown, bullets, symbols, or emojis.

Return exactly:

<message>spoken progress response</message>
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

        if action == PresenceAction.RESPOND.value.upper():
            message = extract_tag(
                content,
                "message",
            )

            if not message:
                return PresenceResult(
                    action=PresenceAction.HANDOFF,
                )

            message = message.strip()

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
            )

        return PresenceResult(
            action=PresenceAction.HANDOFF,
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
