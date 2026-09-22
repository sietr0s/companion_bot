"""OpenAI-compatible chat (OpenRouter, OpenAI, any /v1/chat/completions host)."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from src.modules.llm.presets import DEFAULT_PRESETS, SamplingPreset
from src.modules.llm.providers.invoke import (
    acomplete,
    acomplete_messages,
    resolve_preset,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatChat:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        presets: dict[str, SamplingPreset] | None = None,
    ) -> None:
        self._presets = presets if presets is not None else DEFAULT_PRESETS
        self._llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            base_url=base_url,
            max_retries=2,
        )

    async def complete(self, system: str, user: str, *, preset: str) -> str:
        return await acomplete(self._llm, system, user, resolve_preset(self._presets, preset))

    async def complete_messages(self, messages: list[tuple[str, str]], *, preset: str) -> str:
        return await acomplete_messages(
            self._llm, messages, resolve_preset(self._presets, preset)
        )
