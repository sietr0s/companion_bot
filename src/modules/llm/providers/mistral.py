"""Mistral chat via LangChain ChatMistralAI."""

from __future__ import annotations

from langchain_mistralai import ChatMistralAI

from src.modules.llm.presets import DEFAULT_PRESETS, SamplingPreset
from src.modules.llm.providers.invoke import (
    acomplete,
    acomplete_messages,
    resolve_preset,
)


class MistralChat:
    def __init__(
        self, api_key: str, model: str, presets: dict[str, SamplingPreset] | None = None
    ) -> None:
        self._presets = presets if presets is not None else DEFAULT_PRESETS
        self._llm = ChatMistralAI(
            api_key=api_key,
            model=model,
            max_retries=2,
        )

    async def complete(self, system: str, user: str, *, preset: str) -> str:
        return await acomplete(self._llm, system, user, resolve_preset(self._presets, preset))

    async def complete_messages(self, messages: list[tuple[str, str]], *, preset: str) -> str:
        return await acomplete_messages(self._llm, messages, resolve_preset(self._presets, preset))
