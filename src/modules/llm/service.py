"""LLM module business logic."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

from src.core.bus_topics import BusTopics
from src.domain.chat import message_texts, outgoing_batch
from src.utils.prompt_loader import load_prompt, render_prompt

if TYPE_CHECKING:
    from src.bus.interface import MessageProducer
    from src.modules.llm.embedder import Embedder
    from src.modules.llm.providers.base import ChatProvider
from src.modules.llm.formatting import batches_to_turns, memory_system_suffix
from src.modules.llm.schemas.events import (
    GenerateReplyCommand,
    ReplyGeneratedEvent,
    ReplySuppressedEvent,
    SummarizeCommand,
    SummaryGeneratedEvent,
)

_MAX_QUERY_CHARS = 160
_MAX_QUERY_WORDS = 16


def _sanitize_search_query(raw: str, *, fallback: str) -> str:
    compact_fallback = " ".join((fallback or "").split())[:_MAX_QUERY_CHARS].strip()
    text = (raw or "").strip().strip("\"'")
    if text.lower().startswith("query:"):
        text = text[6:].strip()
    text = " ".join(text.split())
    words = text.split()
    sentences = [
        part for part in text.replace("!", ".").replace("?", ".").split(".") if part.strip()
    ]
    if (
        not text
        or len(text) > _MAX_QUERY_CHARS
        or len(words) > _MAX_QUERY_WORDS
        or len(sentences) > 1
    ):
        return compact_fallback
    return text


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
        summary = command.summary
        retrieved = list(command.retrieved)
        references = list(command.references)
        turns = batches_to_turns(command.recent)
        should_respond = bool(turns) and turns[-1][0] == "human"
        if not should_respond:
            event: ReplyGeneratedEvent | ReplySuppressedEvent = ReplySuppressedEvent(
                conversation_id=command.conversation_id,
                channel=command.channel,
                chat_id=command.chat_id,
                account_id=command.account_id,
                reason="empty_context",
            )
            await self._message_bus.publish(
                BusTopics.LLM_REPLY_SUPPRESSED, event.model_dump(mode="json")
            )
            return event

        system = load_prompt("reply") + "\n\n" + load_prompt("chat_markup")
        extra = memory_system_suffix(summary, retrieved, references)
        if extra:
            system = system + "\n\n" + extra
        chat = self._chat_or_default()
        messages = [("system", system), *turns]
        if hasattr(chat, "complete_messages"):
            text = await chat.complete_messages(messages)
        else:
            text = await chat.complete(system, turns[-1][1])
        batch = outgoing_batch(
            channel=command.channel,
            chat_id=command.chat_id,
            account_id=command.account_id,
            text=text,
        )
        if not batch.messages:
            suppressed = ReplySuppressedEvent(
                conversation_id=command.conversation_id,
                channel=command.channel,
                chat_id=command.chat_id,
                account_id=command.account_id,
                reason="empty_generation",
            )
            await self._message_bus.publish(
                BusTopics.LLM_REPLY_SUPPRESSED, suppressed.model_dump(mode="json")
            )
            return suppressed
        event = ReplyGeneratedEvent(
            conversation_id=command.conversation_id,
            channel=command.channel,
            chat_id=command.chat_id,
            account_id=command.account_id,
            messages=batch.messages,
            batch=batch,
        )
        await self._message_bus.publish(
            BusTopics.LLM_REPLY_GENERATED, event.model_dump(mode="json")
        )
        return event

    async def embed(
        self, texts: list[str], *, role: Literal["query", "document"]
    ) -> list[list[float]]:
        return await asyncio.to_thread(self._embedder.embed, texts, role=role)

    async def retrieve_pre(self, batch_messages: list, fallback: str | None = None) -> str:
        user = "\n".join(message_texts(batch_messages))
        raw = await self._chat_or_default().complete(load_prompt("retrieve_pre"), user)
        return _sanitize_search_query(raw, fallback=fallback or user)

    async def retrieve_post(self, query: str, hits: list[str]) -> list[str]:
        if not hits:
            return []
        user = f"Query:\n{query}\n\nSnippets:\n" + "\n".join(f"- {hit}" for hit in hits)
        raw = await self._chat_or_default().complete(load_prompt("retrieve_post"), user)
        lines = [line.strip().lstrip("- ").strip() for line in raw.splitlines() if line.strip()]
        unused = list(hits)
        kept: list[str] = []
        for line in lines:
            for index, hit in enumerate(unused):
                if line == hit:
                    kept.append(unused.pop(index))
                    break
        return kept

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
        await self._message_bus.publish(
            BusTopics.LLM_SUMMARY_GENERATED, event.model_dump(mode="json")
        )
        return event
