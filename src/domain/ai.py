"""Synchronous application ports exposed by the AI capability.

These interfaces exchange Python/domain values, never provider clients or ORM rows.
Bus commands and events remain in each owning module's schemas/events.py.
"""

from typing import Literal, Protocol


class ChatProvider(Protocol):
    async def complete(self, system: str, user: str, *, preset: str) -> str: ...

    async def complete_messages(self, messages: list[tuple[str, str]], *, preset: str) -> str: ...


class TopicIntelligence(Protocol):
    async def cluster_topics(self, numbered: str) -> str: ...

    async def embed(
        self, texts: list[str], *, role: Literal["query", "document"]
    ) -> list[list[float]]: ...


class MemoryIntelligence(TopicIntelligence, Protocol):
    async def retrieve_pre(self, batch_messages: list, fallback: str | None = None) -> str: ...

    async def retrieve_post(self, query: str, hits: list[str]) -> list[str]: ...

    async def summarize(
        self, current_summary: str | None, messages: list[str], max_chars: int = 1000
    ) -> str: ...
