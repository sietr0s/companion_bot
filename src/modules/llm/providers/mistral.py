"""Mistral chat via LangChain ChatMistralAI."""

from __future__ import annotations

from langchain_mistralai import ChatMistralAI

from src.modules.llm.providers.invoke import acomplete


class MistralChat:
    def __init__(self, api_key: str, model: str) -> None:
        self._llm = ChatMistralAI(
            api_key=api_key,
            model=model,
            temperature=0.3,
            max_retries=2,
        )

    async def complete(self, system: str, user: str) -> str:
        return await acomplete(self._llm, system, user)
