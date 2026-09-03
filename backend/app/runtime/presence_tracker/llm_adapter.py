
from __future__ import annotations

from typing import Any

from app.llm.client import get_client

from .state import PresenceState


class PresenceLLM:

    def __init__(
        self,
        llm: Any | None = None,
        *,
        max_tokens: int = 160,
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

        self._max_tokens = max_tokens

    @property
    def max_tokens(
        self,
    ) -> int:
        return self._max_tokens

    async def generate(
        self,
        *,
        state: PresenceState,
    ) -> str | None:
        prompt = self._build_prompt(state)

        response = await self._llm.ainvoke(
            prompt,
        )

        return self._extract_content(response)

    def _build_prompt(
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
                
                You are participating in an ongoing conversation.

                The user's request is currently being handled, and the work is still
                in progress. Based on the current context below, respond naturally
                to the user.

                Your response should help maintain a natural conversation while the
                work continues.

                Do NOT solve the user's request.
                Do NOT provide the final answer.
                Do NOT expose private reasoning or internal system information.
                Do NOT invent progress or actions that are not present in the state.
                Do NOT repeat the user's request.

                Use only the safe runtime state provided below.

                User request:
                {state.user_request}

                Current status:
                {state.status}

                Current stage:
                {state.stage}

                Current progress:
                {state.message}

                Elapsed time:
                {int(state.elapsed_seconds)} seconds

                Iteration:
                {state.iteration}

                Reasoning step:
                {state.reasoning_step}

                Recently completed steps:
                {completed_steps or "None"}

                Generate a short, natural conversational response based on the
                current situation.

                Rules:
                - Keep the response concise (maximum 1 to 2 sentences).
                - Be natural, warm, and conversational.
                - Acknowledge meaningful progress when available.
                - Do not claim something happened unless the state says it happened.
                - CRITICAL: Do not read back raw system variables to the user. Never mention technical state terms like "iteration", "stage", "seconds elapsed", "reasoning steps", "agents", "tools", or "backend".
                - VOICE INTERFACE COMPLIANCE: Do not use bullet points, markdown formatting, symbols, or emojis. Write out text exactly as it should be spoken aloud.
                - Do not expose chain-of-thought.
                - Do not say "please wait" or "hold on".
                - Do not repeat the user's request.
                - Do not provide the final answer.
                - If there is little useful progress information, give a brief,
                natural acknowledgment that fits the situation.
                """.strip()

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
