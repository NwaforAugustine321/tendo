from __future__ import annotations

import os
os.environ["NEMOGUARDRAILS_LLM_FRAMEWORK"] = "langchain"

import logging
from pathlib import Path
from typing import Any

from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails

from app.guardrails.config import GuardrailConfig, GuardrailResult
from app.llm.client import get_client
import logging
import os

# 1. Turn off usage statistics
os.environ["NEMO_GUARDRAILS_NO_USAGE_STATS"] = "1"

# 2. Block the specific config loader and general rail logs
logging.getLogger("nemoguardrails.rails.llm.config").setLevel(logging.ERROR)
logging.getLogger("nemoguardrails").setLevel(logging.ERROR)

# 3. Global catch-all to force all standard INFO logs from nemoguardrails to shut up
logging.getLogger("nemoguardrails.actions.action_dispatcher").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class GuardrailManager:

    def __init__(self, config: GuardrailConfig) -> None:
        self._config = config
        self._rails_config: RailsConfig | None = None
        self._rails: LLMRails | None = None
        self._runnable: RunnableRails | None = None
        self._initialize()

    def _initialize(self) -> None:
        config_path = Path(self._config.config_dir)

        if not config_path.exists() or not config_path.is_dir():
            raise RuntimeError(f"Guardrails config directory not found: {config_path}")

        try:
            llm = get_client()
            self._rails_config = RailsConfig.from_path(str(config_path))
            self._rails = LLMRails(self._rails_config, llm=llm)
            self._runnable = RunnableRails(config=self._rails_config, llm=llm, passthrough=False)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize NeMo Guardrails: {exc}") from exc

    @property
    def guardrails(self) -> RunnableRails | None:
        return self._rails

    async def validate_input(self, messages: list[dict]) -> GuardrailResult:
        try:
            result = await self._rails.generate_async(messages=messages)
            print(result)
            output = result.get("content", "") if isinstance(result, dict) else str(result)
            
            return GuardrailResult(allowed=True, response=output)
        except Exception as e:
            logger.warning(f"Input validation failed: {e}")
            return GuardrailResult(allowed=True, response=None)

    async def validate_dialog(self, messages: list[dict]) -> GuardrailResult:
        try:
            result = await self._rails.generate_async(messages=messages)
            output = result.get("content", "") if isinstance(result, dict) else str(result)
            return GuardrailResult(allowed=True, response=output)
        except Exception as e:
            logger.warning(f"Dialog validation failed: {e}")
            return GuardrailResult(allowed=True, response=None)

    async def validate_output(self, response: str) -> GuardrailResult:
        try:
            messages = [{"role": "assistant", "content": response}]
            result = await self._rails.generate_async(messages=messages)
            output = result.get("content", "") if isinstance(result, dict) else str(result)
            return GuardrailResult(allowed=True, response=output)
        except Exception as e:
            logger.warning(f"Output validation failed: {e}")
            return GuardrailResult(allowed=True, response=response)

    async def validate_tool_input(self, tool_name: str, tool_args: dict) -> GuardrailResult:
        try:
            messages = [{"role": "user", "content": f"Calling tool: {tool_name} with args: {tool_args}"}]
            result = await self._rails.generate_async(messages=messages)
            output = result.get("content", "") if isinstance(result, dict) else str(result)
            return GuardrailResult(allowed=True, response=output)
        except Exception as e:
            logger.warning(f"Tool input validation failed: {e}")
            return GuardrailResult(allowed=True, response=None)

    async def validate_tool_output(self, tool_name: str, tool_result: str) -> GuardrailResult:
        try:
            messages = [{"role": "tool", "content": f"Tool {tool_name} returned: {tool_result}"}]
            result = await self._rails.generate_async(messages=messages)
            output = result.get("content", "") if isinstance(result, dict) else str(result)
            return GuardrailResult(allowed=True, response=output)
        except Exception as e:
            logger.warning(f"Tool output validation failed: {e}")
            return GuardrailResult(allowed=True, response=tool_result)

    async def release(self) -> None:
        self._rails = None
        self._runnable = None
