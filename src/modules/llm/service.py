"""LLM module business logic."""

from __future__ import annotations

import asyncio
from typing import Literal

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.domain.chat import message_texts, outgoing_batch
from src.modules.llm.embedder import Embedder
from src.modules.llm.prompts import load_prompt, render_prompt
from src.modules.llm.providers.base import ChatProvider
from src.modules.llm.schemas.events import (
    GenerateReplyCommand,
    ReplyGeneratedEvent,
    ReplySuppressedEvent,
    SummarizeCommand,
    SummaryGeneratedEvent,
)


class LLMService:
    def __init__(
        self,
        message_bus: MessageProducer,
        embedder: Embedder,
        chat: ChatProvider | None = None,
    ) -> None:
        self._message_bus = message_bus
        self._embedder = embedder
        self._chat = chat

    def _chat_or_default(self) -> ChatProvider:
        if self._chat is None:
            from src.modules.llm.dependencies import get_chat_provider

            self._chat = get_chat_provider()
        return self._chat

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

        system = load_prompt("reply") + "\n\n" + load_prompt("chat_markup")
        text = await self._chat_or_default().complete(system, command.context)
        batch = outgoing_batch(
            telegram_chat_id=command.telegram_chat_id,
            telegram_account_id=command.telegram_account_id,
            text=text,
        )
        if not batch.messages:
            suppressed = ReplySuppressedEvent(
                conversation_id=command.conversation_id,
                telegram_chat_id=command.telegram_chat_id,
                telegram_account_id=command.telegram_account_id,
                reason="empty_generation",
            )
            await self._message_bus.publish(BusTopics.LLM_REPLY_SUPPRESSED, suppressed.to_bus_dict())
            return suppressed
        event = ReplyGeneratedEvent(
            conversation_id=command.conversation_id,
            telegram_chat_id=command.telegram_chat_id,
            telegram_account_id=command.telegram_account_id,
            messages=batch.messages,
            batch=batch,
        )
        await self._message_bus.publish(BusTopics.LLM_REPLY_GENERATED, event.to_bus_dict())
        return event

    async def embed(
        self, texts: list[str], *, role: Literal["query", "document"]
    ) -> list[list[float]]:
        return await asyncio.to_thread(self._embedder.embed, texts, role=role)

    async def retrieve_pre(self, batch_messages: list) -> str:
        user = "\n".join(message_texts(batch_messages))
        return await self._chat_or_default().complete(load_prompt("retrieve_pre"), user)

    async def retrieve_post(self, query: str, hits: list[str]) -> list[str]:
        if not hits:
            return []
        prompt = render_prompt(
            "retrieve_post",
            query=query,
            messages="\n".join(f"- {hit}" for hit in hits),
        )
        raw = await self._chat_or_default().complete(prompt, prompt)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return lines or hits

    async def cluster_topics(self, numbered: str) -> str:
        prompt = render_prompt("cluster_topics", messages=numbered)
        return await self._chat_or_default().complete(prompt, numbered)

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
        prompt = render_prompt("summarize", messages="\n".join(parts))
        text = await self._chat_or_default().complete(prompt, prompt)
        return text[:max_chars]

    async def summarize_command(self, command: SummarizeCommand) -> SummaryGeneratedEvent:
        summary = await self.summarize(None, command.messages, command.max_chars)
        event = SummaryGeneratedEvent(
            conversation_id=command.conversation_id,
            summary=summary,
            char_count=len(summary),
        )
        await self._message_bus.publish(BusTopics.LLM_SUMMARY_GENERATED, event.to_bus_dict())
        return event
