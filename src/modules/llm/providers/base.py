"""Chat completion interface for LLM providers."""

from __future__ import annotations

from typing import Protocol


class ChatProvider(Protocol):
    async def complete(self, system: str, user: str) -> str: ...
