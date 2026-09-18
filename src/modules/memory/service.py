"""Memory module business logic."""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import NotFoundError
from src.domain.chat import ChatRef, Topic, display_text
from src.modules.llm.service import LLMService
from src.modules.memory.clustering import (
    normalize_cluster_blocks,
    parse_cluster_json,
    split_closed_open,
)
from src.modules.memory.constants import (
    CLUSTER_HARD_CAP,
    CLUSTER_MIN_MESSAGES,
    CLUSTER_RETRIES,
    RETRIEVE_PRE_WINDOW,
    SNIPPET_MAX_MESSAGES,
    SUMMARY_THRESHOLD,
    TOPIC_EMBED_MAX_CHARS,
    VECTOR_TOP_K,
)
from src.modules.memory.exceptions import ConversationNotFoundError
from src.modules.memory.formatting import (
    numbered_window,
    retrieve_pre_input,
    topic_embed_text,
)
from src.modules.memory.mapping import to_domain_batches, to_topic
from src.modules.memory.models import Conversation, Message, SummaryState, VectorRecord
from src.modules.memory.repository import (
    ConversationRepository,
    MessageBatchRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.schemas.events import (
    BatchProcessedEvent,
    BuildContextCommand,
    ContextBuiltEvent,
    MaintainMemoryCommand,
    MemoryUpdatedEvent,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)
from src.modules.memory.schemas.public import (
    MemoryMessageRead,
    VectorTopicDetailRead,
    VectorTopicRead,
)

logger = logging.getLogger(__name__)


def _topic_read(record: VectorRecord, message_count: int) -> VectorTopicRead:
    return VectorTopicRead(
        id=record.id,
        conversation_id=record.conversation_id,
        title=record.text,
        seq_from=record.seq_from,
        seq_to=record.seq_to,
        message_count=message_count,
        kind=record.kind,
        partial=record.partial,
        created_at=record.created_at,
    )


class ConversationService(BaseService[ConversationRepository, Conversation]):
    def __init__(self, repository: ConversationRepository) -> None:
        super().__init__(repository)


class MessageService(BaseService[MessageRepository, Message]):
    def __init__(self, repository: MessageRepository) -> None:
        super().__init__(repository)


class SummaryStateService(BaseService[SummaryStateRepository, SummaryState]):
    def __init__(self, repository: SummaryStateRepository) -> None:
        super().__init__(repository)


class VectorRecordService(BaseService[VectorRecordRepository, VectorRecord]):
    def __init__(self, repository: VectorRecordRepository) -> None:
        super().__init__(repository)


class MemoryService:
    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        summaries: SummaryStateRepository,
        vectors: VectorRecordRepository,
        message_bus: MessageProducer,
        llm: LLMService,
        batches: MessageBatchRepository | None = None,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._batches = batches or MessageBatchRepository()
        self._summaries = summaries
        self._vectors = vectors
        self._message_bus = message_bus
        self._llm = llm
        self._maintain_locks: dict[UUID, asyncio.Lock] = {}

    async def list_topics(
        self, session: AsyncSession, conversation_id: UUID
    ) -> list[VectorTopicRead]:
        rows = await self._vectors.list_for_conversation(session, conversation_id)
        topics: list[VectorTopicRead] = []
        for row in rows:
            topics.append(_topic_read(row, row.seq_to - row.seq_from + 1))
        topics.sort(key=lambda item: item.seq_from)
        return topics

    async def get_topic(
        self, session: AsyncSession, conversation_id: UUID, topic_id: UUID
    ) -> VectorTopicDetailRead:
        record = await self._vectors.get_by_id(session, topic_id)
        if record is None or record.conversation_id != conversation_id:
            raise NotFoundError(detail="Тема не найдена")
        seq_from, seq_to = record.seq_from, record.seq_to
        messages = await self._messages.get_between_inclusive(
            session, conversation_id, seq_from, seq_to
        )
        base = _topic_read(record, len(messages))
        return VectorTopicDetailRead(
            **base.model_dump(),
            messages=[MemoryMessageRead.model_validate(m) for m in messages],
        )

    async def _maybe_cluster(
        self,
        session: AsyncSession,
        *,
        conversation_id: UUID,
    ) -> None:
        summary_state = await self._summaries.get_by_conversation_id(session, conversation_id)
        checkpoint = summary_state.cluster_checkpoint if summary_state else 0
        window = await self._messages.get_after_checkpoint(session, conversation_id, checkpoint)
        if len(window) < CLUSTER_MIN_MESSAGES:
            return
        hard_cap = len(window) >= CLUSTER_HARD_CAP
        if hard_cap:
            window = window[:CLUSTER_HARD_CAP]
        seqs = [m.sequence_number for m in window]
        by_seq = {m.sequence_number: m for m in window}
        numbered = numbered_window(window)
        parsed = None
        try:
            for attempt in range(1, CLUSTER_RETRIES + 1):
                raw = await self._llm.cluster_topics(numbered)
                blocks = parse_cluster_json(raw)
                if blocks is None:
                    logger.warning("cluster JSON invalid attempt %s", attempt)
                    continue
                blocks = normalize_cluster_blocks(blocks, seqs)
                if blocks is None:
                    continue
                split = split_closed_open(blocks, seqs, hard_cap=hard_cap)
                if split is None:
                    continue
                parsed = split
                break
            if parsed is None:
                return
            closed, _open_ids = parsed
            topic_payloads: list[tuple] = []
            embed_texts: list[str] = []
            max_closed = checkpoint
            for block in closed:
                max_closed = max(max_closed, block.ids[-1])
                if block.kind != "topic":
                    continue
                msgs = [
                    (by_seq[seq].direction, by_seq[seq].text) for seq in block.ids if seq in by_seq
                ]
                embed_texts.append(
                    topic_embed_text(block.topic, msgs, max_chars=TOPIC_EMBED_MAX_CHARS)
                )
                topic_payloads.append((block, msgs))
            embeddings = await self._llm.embed(embed_texts, role="document") if embed_texts else []
            for (block, _msgs), embedding in zip(topic_payloads, embeddings, strict=True):
                await self._vectors.create(
                    session,
                    {
                        "conversation_id": conversation_id,
                        "text": block.topic,
                        "kind": "topic",
                        "embedding": embedding,
                        "seq_from": block.ids[0],
                        "seq_to": block.ids[-1],
                        "partial": hard_cap,
                    },
                )
            await self._summaries.upsert_cluster_checkpoint(session, conversation_id, max_closed)
        except Exception:
            logger.exception("failed to cluster topics")

    async def _maybe_summarize(
        self,
        session: AsyncSession,
        *,
        conversation_id: UUID,
        current_sequence: int,
    ) -> bool:
        summary_state = await self._summaries.get_by_conversation_id(session, conversation_id)
        checkpoint = summary_state.checkpoint if summary_state else 0
        current_summary = summary_state.current_summary if summary_state else None
        if current_sequence - checkpoint < SUMMARY_THRESHOLD:
            return False
        try:
            after = await self._messages.get_after_checkpoint(session, conversation_id, checkpoint)
            new_summary = await self._llm.summarize(current_summary, [m.text for m in after])
            await self._summaries.upsert(
                session,
                conversation_id,
                new_summary,
                current_sequence,
            )
            return True
        except Exception:
            logger.exception("failed to summarize conversation")
            return False

    async def process_batch(
        self, session: AsyncSession, command: ProcessBatchCommand
    ) -> BatchProcessedEvent:
        batch = command.batch
        direction = batch.direction
        conversation = await self._conversations.get_or_create(
            session,
            telegram_chat_id=batch.chat_id,
            telegram_account_id=batch.account_id,
        )

        sequence_numbers: list[int] = []
        current_sequence = conversation.last_sequence_number
        if batch.messages:
            batch_row = await self._batches.create(
                session,
                {
                    "id": batch.id,
                    "conversation_id": conversation.id,
                    "direction": direction,
                },
            )
            first_seq = await self._conversations.allocate_sequence_numbers(
                session, conversation.id, len(batch.messages)
            )
            for offset, msg in enumerate(batch.messages):
                current_sequence = first_seq + offset
                await self._messages.create(
                    session,
                    {
                        "conversation_id": conversation.id,
                        "batch_id": batch_row.id,
                        "text": display_text(msg),
                        "direction": direction,
                        "message_type": msg.message_type,
                        "sequence_number": current_sequence,
                    },
                )
                sequence_numbers.append(current_sequence)

        await self._conversations.update(
            session,
            conversation,
            {
                "last_activity_at": datetime.now(UTC),
            },
        )

        event_batch_processed = BatchProcessedEvent(
            conversation_id=conversation.id,
            channel=batch.channel,
            chat_id=conversation.telegram_chat_id,
            account_id=conversation.telegram_account_id,
        )
        event_memory_maintain = MaintainMemoryCommand(
            conversation_id=conversation.id,
            channel=batch.channel,
            chat_id=conversation.telegram_chat_id,
            account_id=conversation.telegram_account_id,
            current_sequence=current_sequence,
        )
        await self._message_bus.publish(
            BusTopics.MEMORY_BATCH_PROCESSED, event_batch_processed.model_dump(mode="json")
        )
        await self._message_bus.publish(
            BusTopics.MEMORY_MAINTAIN, event_memory_maintain.model_dump(mode="json")
        )
        return event_batch_processed

    def _maintain_lock(self, conversation_id: UUID) -> asyncio.Lock:
        lock = self._maintain_locks.get(conversation_id)
        if lock is None:
            lock = asyncio.Lock()
            self._maintain_locks[conversation_id] = lock
        return lock

    async def maintain_memory(self, session: AsyncSession, command: MaintainMemoryCommand) -> None:
        async with self._maintain_lock(command.conversation_id):
            await self._maybe_cluster(session, conversation_id=command.conversation_id)
            if command.current_sequence:
                await self._maybe_summarize(
                    session,
                    conversation_id=command.conversation_id,
                    current_sequence=command.current_sequence,
                )

    async def _retrieve_snippets(
        self,
        session: AsyncSession,
        *,
        query: str,
        query_embedding: list[float],
        conversation_id: UUID | None,
        kind: str,
        recent_min_seq: int | None = None,
        chat: ChatRef,
    ) -> list[Topic]:
        hits = await self._vectors.search_similar(
            session,
            conversation_id,
            query_embedding,
            VECTOR_TOP_K,
            kind=kind,
        )
        ranked = await self._llm.retrieve_post(query, [h.text for h in hits])
        unused = list(hits)
        topics: list[Topic] = []
        for title in ranked:
            hit = None
            for index, candidate in enumerate(unused):
                if candidate.text == title:
                    hit = unused.pop(index)
                    break
            if hit is None:
                continue
            seq_from, seq_to = hit.seq_from, hit.seq_to
            if recent_min_seq is not None and seq_from >= recent_min_seq:
                continue
            if recent_min_seq is not None:
                seq_to = min(seq_to, recent_min_seq - 1)
            if seq_to < seq_from:
                continue
            msgs = await self._messages.get_between_inclusive(
                session, hit.conversation_id, seq_from, seq_to
            )
            if SNIPPET_MAX_MESSAGES > 0 and len(msgs) > SNIPPET_MAX_MESSAGES:
                msgs = msgs[-SNIPPET_MAX_MESSAGES:]
            conv = await self._conversations.get_by_id(session, hit.conversation_id)
            topic_chat = ChatRef(
                channel=chat.channel,
                chat_id=conv.telegram_chat_id if conv else chat.chat_id,
                account_id=conv.telegram_account_id if conv else chat.account_id,
                conversation_id=hit.conversation_id,
            )
            topics.append(
                to_topic(
                    title=title,
                    kind=hit.kind,
                    conversation_id=hit.conversation_id,
                    seq_from=seq_from,
                    seq_to=seq_to,
                    batches=to_domain_batches(msgs, topic_chat),
                )
            )
        return topics

    async def build_context(
        self, session: AsyncSession, command: BuildContextCommand
    ) -> ContextBuiltEvent:
        messages = await self._messages.get_last_messages(
            session,
            conversation_id=command.conversation_id,
            limit=command.last_n_messages,
        )
        summary_state = await self._summaries.get_by_conversation_id(
            session, command.conversation_id
        )
        summary = summary_state.current_summary if summary_state else None
        chat = ChatRef(
            channel=command.channel,
            chat_id=command.chat_id,
            account_id=command.account_id,
            conversation_id=command.conversation_id,
        )
        recent_batches = to_domain_batches(messages, chat)
        recent_pairs = [(msg.direction, msg.text) for msg in messages]

        retrieved: list[Topic] = []
        references: list[Topic] = []
        recent_min_seq = messages[0].sequence_number if messages else None
        try:
            pre_lines, pre_fallback = retrieve_pre_input(recent_pairs, RETRIEVE_PRE_WINDOW)
            query = await self._llm.retrieve_pre(pre_lines, fallback=pre_fallback)
            qvec = (await self._llm.embed([query], role="query"))[0]
            retrieved = await self._retrieve_snippets(
                session,
                query=query,
                query_embedding=qvec,
                conversation_id=command.conversation_id,
                kind="topic",
                recent_min_seq=recent_min_seq,
                chat=chat,
            )
            references = await self._retrieve_snippets(
                session,
                query=query,
                query_embedding=qvec,
                conversation_id=None,
                kind="reference",
                chat=chat,
            )
        except Exception:
            logger.exception("retrieve failed")
            retrieved = []
            references = []

        event = ContextBuiltEvent(
            conversation_id=command.conversation_id,
            channel=command.channel,
            chat_id=command.chat_id,
            account_id=command.account_id,
            retrieved_count=len(retrieved),
            summary=summary,
            retrieved=retrieved,
            references=references,
            recent=recent_batches,
        )
        await self._message_bus.publish(
            BusTopics.MEMORY_CONTEXT_BUILT, event.model_dump(mode="json")
        )
        return event

    async def update_memory(
        self, session: AsyncSession, command: UpdateMemoryCommand
    ) -> MemoryUpdatedEvent:
        conversation = await self._conversations.get_by_id(session, command.conversation_id)
        if not conversation:
            raise ConversationNotFoundError(f"Conversation {command.conversation_id} not found")

        conversation_id = conversation.id
        telegram_chat_id = conversation.telegram_chat_id
        messages_saved = 0
        summary_updated = False
        if command.delivery_status == "delivered" and command.outgoing_messages:
            batch_row = await self._batches.create(
                session,
                {
                    "conversation_id": conversation_id,
                    "direction": "outgoing",
                },
            )
            first_seq = await self._conversations.allocate_sequence_numbers(
                session, conversation_id, len(command.outgoing_messages)
            )
            sequence_numbers: list[int] = []
            current_sequence = first_seq
            message_type = "voice" if command.message_type == "voice" else "text"
            for offset, text in enumerate(command.outgoing_messages):
                current_sequence = first_seq + offset
                await self._messages.create(
                    session,
                    {
                        "conversation_id": conversation_id,
                        "batch_id": batch_row.id,
                        "text": text,
                        "direction": "outgoing",
                        "message_type": message_type,
                        "sequence_number": current_sequence,
                    },
                )
                sequence_numbers.append(current_sequence)
                messages_saved += 1
        event = MemoryUpdatedEvent(
            conversation_id=conversation_id,
            channel=command.channel,
            chat_id=telegram_chat_id,
            account_id=conversation.telegram_account_id,
            messages_count=messages_saved,
            summary_updated=summary_updated,
        )
        await self._message_bus.publish(BusTopics.MEMORY_UPDATED, event.model_dump(mode="json"))
        if messages_saved:
            await self._message_bus.publish(
                BusTopics.MEMORY_MAINTAIN,
                MaintainMemoryCommand(
                    conversation_id=conversation_id,
                    channel=command.channel,
                    chat_id=telegram_chat_id,
                    account_id=conversation.telegram_account_id,
                    current_sequence=current_sequence,
                ).model_dump(mode="json"),
            )
        return event
