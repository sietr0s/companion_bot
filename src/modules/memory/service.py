"""Memory module business logic."""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.llm.service import LLMService
from src.modules.memory.clustering import parse_cluster_json, split_closed_open
from src.modules.memory.constants import (
    CLUSTER_HARD_CAP,
    CLUSTER_MIN_MESSAGES,
    SUMMARY_THRESHOLD,
    VECTOR_TOP_K,
)
from src.modules.memory.exceptions import ConversationNotFoundError
from src.domain.chat import display_text, message_texts
from src.modules.memory.formatting import (
    assemble_context,
    format_topic_snippet,
    numbered_window,
)
from src.modules.memory.models import Conversation, Message, SummaryState, VectorRecord
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.schemas.events import (
    BatchProcessedEvent,
    BuildContextCommand,
    ContextBuiltEvent,
    MemoryUpdatedEvent,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)

logger = logging.getLogger(__name__)


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
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._summaries = summaries
        self._vectors = vectors
        self._message_bus = message_bus
        self._llm = llm

    async def _maybe_cluster(
        self,
        session: AsyncSession,
        *,
        conversation_id: UUID,
    ) -> None:
        summary_state = await self._summaries.get_by_conversation_id(
            session, conversation_id
        )
        checkpoint = summary_state.cluster_checkpoint if summary_state else 0
        window = await self._messages.get_after_checkpoint(
            session, conversation_id, checkpoint
        )
        if len(window) < CLUSTER_MIN_MESSAGES:
            return
        hard_cap = len(window) >= CLUSTER_HARD_CAP
        if hard_cap:
            window = window[:CLUSTER_HARD_CAP]
        try:
            raw = await self._llm.cluster_topics(numbered_window(window))
            parsed = parse_cluster_json(raw)
            if parsed is None:
                return
            split = split_closed_open(
                parsed,
                [m.sequence_number for m in window],
                hard_cap=hard_cap,
            )
            if split is None:
                return
            closed, _open_ids = split
            topics = [b.topic for b in closed if b.kind == "topic"]
            embeddings = await self._llm.embed(topics, role="document") if topics else []
            ei = 0
            max_closed = checkpoint
            for block in closed:
                max_closed = max(max_closed, block.ids[-1])
                if block.kind != "topic":
                    continue
                await self._vectors.create(
                    session,
                    {
                        "conversation_id": conversation_id,
                        "text": block.topic,
                        "embedding": embeddings[ei],
                        "extra_data": {
                            "kind": "topic",
                            "seq_from": block.ids[0],
                            "seq_to": block.ids[-1],
                            "partial": hard_cap,
                        },
                    },
                )
                ei += 1
            await self._summaries.upsert_cluster_checkpoint(
                session, conversation_id, max_closed
            )
        except Exception:
            logger.exception("failed to cluster topics")

    async def _maybe_summarize(
        self,
        session: AsyncSession,
        *,
        conversation_id: UUID,
        current_sequence: int,
    ) -> bool:
        summary_state = await self._summaries.get_by_conversation_id(
            session, conversation_id
        )
        checkpoint = summary_state.checkpoint if summary_state else 0
        current_summary = summary_state.current_summary if summary_state else None
        if current_sequence - checkpoint < SUMMARY_THRESHOLD:
            return False
        try:
            after = await self._messages.get_after_checkpoint(
                session, conversation_id, checkpoint
            )
            new_summary = await self._llm.summarize(
                current_summary, [m.text for m in after]
            )
            await self._summaries.upsert(
                session,
                conversation_id,
                new_summary,
                current_sequence,
            )
            return True
        except Exception:
            logger.exception("failed to summarize conversation")
            await session.rollback()
            return False

    async def process_batch(
        self, session: AsyncSession, command: ProcessBatchCommand
    ) -> BatchProcessedEvent:
        conversation = await self._conversations.get_or_create(
            session,
            telegram_chat_id=command.telegram_chat_id,
            user_id=command.conversation_id or uuid4(),
        )
        if command.telegram_account_id is not None:
            conversation = await self._conversations.update(
                session,
                conversation,
                {"telegram_account_id": command.telegram_account_id},
            )

        current_sequence = conversation.last_sequence_number
        sequence_numbers = []
        for msg in command.messages:
            current_sequence += 1
            await self._messages.create(
                session,
                {
                    "conversation_id": conversation.id,
                    "text": display_text(msg),
                    "direction": command.direction,
                    "message_type": msg.message_type,
                    "sequence_number": current_sequence,
                    "batch_id": command.batch_id,
                },
            )
            sequence_numbers.append(current_sequence)

        await self._conversations.update(
            session,
            conversation,
            {
                "last_sequence_number": current_sequence,
                "last_activity_at": datetime.now(UTC),
            },
        )

        conversation_id = conversation.id
        telegram_chat_id = conversation.telegram_chat_id
        telegram_account_id = conversation.telegram_account_id

        await self._maybe_cluster(
            session,
            conversation_id=conversation_id,
        )
        await self._maybe_summarize(
            session,
            conversation_id=conversation_id,
            current_sequence=current_sequence,
        )

        event = BatchProcessedEvent(
            conversation_id=conversation_id,
            telegram_chat_id=telegram_chat_id,
            telegram_account_id=telegram_account_id,
            sequence_numbers=sequence_numbers,
            messages=list(command.messages),
        )
        await self._message_bus.publish(BusTopics.MEMORY_BATCH_PROCESSED, event.to_bus_dict())
        return event

    async def build_context(
        self, session: AsyncSession, command: BuildContextCommand
    ) -> ContextBuiltEvent:
        messages = await self._messages.get_last_messages(
            session,
            conversation_id=command.conversation_id,
            limit=command.last_n_messages,
        )
        summary_state = await self._summaries.get_by_conversation_id(session, command.conversation_id)
        summary = summary_state.current_summary if summary_state else None
        recent = [(msg.direction, msg.text) for msg in messages]

        retrieved: list[str] = []
        try:
            query = await self._llm.retrieve_pre(message_texts(command.batch_messages))
            qvec = (await self._llm.embed([query], role="query"))[0]
            hits = await self._vectors.search_similar(
                session, command.conversation_id, qvec, VECTOR_TOP_K
            )
            ranked_topics = await self._llm.retrieve_post(
                query, [h.text for h in hits]
            )
            by_topic = {h.text: h for h in hits}
            for topic in ranked_topics:
                hit = by_topic.get(topic)
                if hit is None:
                    retrieved.append(topic)
                    continue
                extra = hit.extra_data or {}
                seq_from = extra.get("seq_from")
                seq_to = extra.get("seq_to")
                if seq_from is None or seq_to is None:
                    retrieved.append(hit.text)
                    continue
                msgs = await self._messages.get_between_inclusive(
                    session, command.conversation_id, int(seq_from), int(seq_to)
                )
                retrieved.append(
                    format_topic_snippet(
                        topic, [(m.direction, m.text) for m in msgs]
                    )
                )
        except Exception:
            logger.exception("retrieve failed")
            await session.rollback()
            retrieved = []

        context = assemble_context(
            summary=summary,
            retrieved=retrieved,
            recent=recent,
        )

        event = ContextBuiltEvent(
            conversation_id=command.conversation_id,
            telegram_chat_id=command.telegram_chat_id,
            telegram_account_id=command.telegram_account_id,
            context=context,
            retrieved_count=len(retrieved),
        )
        await self._message_bus.publish(BusTopics.MEMORY_CONTEXT_BUILT, event.to_bus_dict())
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
        if command.delivery_status == "delivered":
            current_sequence = conversation.last_sequence_number
            sequence_numbers: list[int] = []
            for text in command.outgoing_messages:
                current_sequence += 1
                await self._messages.create(
                    session,
                    {
                        "conversation_id": conversation_id,
                        "text": text,
                        "direction": "outgoing",
                        "message_type": "text",
                        "sequence_number": current_sequence,
                    },
                )
                sequence_numbers.append(current_sequence)
                messages_saved += 1
            if messages_saved:
                await self._conversations.update(
                    session,
                    conversation,
                    {"last_sequence_number": current_sequence},
                )
                await self._maybe_cluster(
                    session,
                    conversation_id=conversation_id,
                )
                summary_updated = await self._maybe_summarize(
                    session,
                    conversation_id=conversation_id,
                    current_sequence=current_sequence,
                )

        event = MemoryUpdatedEvent(
            conversation_id=conversation_id,
            telegram_chat_id=telegram_chat_id,
            messages_count=messages_saved,
            summary_updated=summary_updated,
        )
        await self._message_bus.publish(BusTopics.MEMORY_UPDATED, event.to_bus_dict())
        return event
