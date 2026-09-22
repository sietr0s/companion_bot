"""Chat completion interface for LLM providers."""

from __future__ import annotations

from typing import Protocol


class ChatProvider(Protocol):
    async def complete(self, system: str, user: str, *, preset: str) -> str: ...

    async def complete_messages(self, messages: list[tuple[str, str]], *, preset: str) -> str: ...
