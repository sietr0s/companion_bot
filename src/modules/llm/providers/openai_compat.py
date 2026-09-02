"""OpenAI-compatible chat (OpenRouter, OpenAI, any /v1/chat/completions host)."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from src.modules.llm.providers.invoke import acomplete

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatChat:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self._llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=0.3,
            max_retries=2,
        )

    async def complete(self, system: str, user: str) -> str:
        return await acomplete(self._llm, system, user)
