"""LLM module business logic (stub provider)."""

from __future__ import annotations

import asyncio
from typing import Literal

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.llm.embedder import Embedder
from src.modules.llm.schemas.events import (
    GenerateReplyCommand,
    ReplyGeneratedEvent,
    ReplySuppressedEvent,
    SummarizeCommand,
    SummaryGeneratedEvent,
)


class LLMService:
    def __init__(self, message_bus: MessageProducer, embedder: Embedder) -> None:
        self._message_bus = message_bus
        self._embedder = embedder

    async def generate_reply(
        self,
        command: GenerateReplyCommand,
    ) -> ReplyGeneratedEvent | ReplySuppressedEvent:
        should_respond = bool(command.context.strip())
        if not should_respond:
            event: ReplyGeneratedEvent | ReplySuppressedEvent = ReplySuppressedEvent(
                conversation_id=command.conversation_id,
                telegram_chat_id=command.telegram_chat_id,
                telegram_account_id=command.telegram_account_id,
                reason="empty_context",
            )
            await self._message_bus.publish(BusTopics.LLM_REPLY_SUPPRESSED, event.to_bus_dict())
            return event

        last_line = command.context.strip().splitlines()[-1]
        event = ReplyGeneratedEvent(
            conversation_id=command.conversation_id,
            telegram_chat_id=command.telegram_chat_id,
            telegram_account_id=command.telegram_account_id,
            messages=[f"Got it: {last_line}"],
        )
        await self._message_bus.publish(BusTopics.LLM_REPLY_GENERATED, event.to_bus_dict())
        return event

    async def embed(
        self, texts: list[str], *, role: Literal["query", "document"]
    ) -> list[list[float]]:
        return await asyncio.to_thread(self._embedder.embed, texts, role=role)

    async def retrieve_pre(self, batch_messages: list[str]) -> str:
        return "\n".join(batch_messages)

    async def retrieve_post(self, query: str, hits: list[str]) -> list[str]:
        return hits

    async def summarize(
        self,
        current_summary: str | None,
        messages: list[str],
        max_chars: int = 1000,
    ) -> str:
        parts: list[str] = []
        if current_summary:
            parts.append(current_summary)
        parts.extend(messages)
        return "\n".join(parts)[:max_chars]

    async def summarize_command(self, command: SummarizeCommand) -> SummaryGeneratedEvent:
        summary = await self.summarize(None, command.messages, command.max_chars)
        event = SummaryGeneratedEvent(
            conversation_id=command.conversation_id,
            summary=summary,
            char_count=len(summary),
        )
        await self._message_bus.publish(BusTopics.LLM_SUMMARY_GENERATED, event.to_bus_dict())
        return event
