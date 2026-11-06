"""Persistence adapters: ORM rows stay here, business reads return domain entities."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import delete, func, select, update

from src.base.repository import BaseRepository
from src.modules.memory.domain import (
    ConversationState,
    HistoryMessage,
    IndexedTopic,
    NewMessage,
    RollingSummary,
)
from src.modules.memory.models import (
    Conversation,
    Message,
    MessageBatch,
    SummaryState,
    VectorRecord,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.domain.chat import Channel


def _conversation(row: Conversation) -> ConversationState:
    return ConversationState(
        row.id, cast("Channel", row.channel), row.chat_id, row.account_id, row.last_sequence_number
    )


def _message(row: Message) -> HistoryMessage:
    return HistoryMessage(
        row.id,
        row.conversation_id,
        row.batch_id,
        row.text,
        row.direction,
        row.message_type,
        row.sequence_number,
        row.created_at,
        row.updated_at,
    )


def _topic(row: VectorRecord) -> IndexedTopic:
    return IndexedTopic(
        conversation_id=row.conversation_id,
        text=row.text,
        seq_from=row.seq_from,
        seq_to=row.seq_to,
        kind=row.kind,
        partial=row.partial,
        embedding=row.embedding,
        id=row.id,
        created_at=row.created_at,
    )


def _cosine_distance(a: list[float], b: list[float]) -> float | None:
    """Return 1 - cosine similarity, or None if either vector has zero length."""
    if len(a) != len(b):
        return None
    dot = 0.0
    n1 = 0.0
    n2 = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        n1 += x * x
        n2 += y * y
    if n1 == 0.0 or n2 == 0.0:
        return None
    return 1.0 - (dot / (math.sqrt(n1) * math.sqrt(n2)))


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self) -> None:
        super().__init__(Conversation)

    async def get_by_chat_id(
        self, session: AsyncSession, chat_id: int, *, channel: str = "telegram"
    ) -> Conversation | None:
        result = await session.execute(
            select(Conversation).where(
                Conversation.channel == channel,
                Conversation.chat_id == chat_id,
            )
        )
        return result.scalars().first()

    async def get_by_channel_chat_account(
        self,
        session: AsyncSession,
        *,
        channel: str,
        chat_id: int,
        account_id: UUID | None,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.channel == channel,
            Conversation.chat_id == chat_id,
        )
        if account_id is None:
            stmt = stmt.where(Conversation.account_id.is_(None))
        else:
            stmt = stmt.where(Conversation.account_id == account_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        session: AsyncSession,
        *,
        channel: str,
        chat_id: int,
        account_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> ConversationState:
        conversation = await self.get_by_channel_chat_account(
            session, channel=channel, chat_id=chat_id, account_id=account_id
        )
        if conversation:
            return _conversation(conversation)
        conversation = await self.create(
            session,
            {
                "channel": channel,
                "chat_id": chat_id,
                "user_id": user_id,
                "account_id": account_id,
            },
        )
        return _conversation(conversation)

    async def get_state(
        self, session: AsyncSession, conversation_id: UUID
    ) -> ConversationState | None:
        row = await self.get_by_id(session, conversation_id)
        return _conversation(row) if row is not None else None

    async def allocate_sequence_numbers(
        self, session: AsyncSession, conversation_id: UUID, count: int
    ) -> int:
        """Atomically bump last_sequence_number; return the first new number."""
        if count < 1:
            raise ValueError("count must be >= 1")
        result = await session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_sequence_number=Conversation.last_sequence_number + count)
            .returning(Conversation.last_sequence_number)
        )
        last = result.scalar_one()
        await session.flush()
        return last - count + 1


class MessageBatchRepository(BaseRepository[MessageBatch]):
    def __init__(self) -> None:
        super().__init__(MessageBatch)

    async def delete_for_conversation(self, session: AsyncSession, conversation_id: UUID) -> None:
        """Delete empty batches after their messages have been removed."""
        await session.execute(
            delete(MessageBatch).where(MessageBatch.conversation_id == conversation_id)
        )
        await session.flush()

    async def append_messages(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        direction: str,
        messages: list[NewMessage],
        *,
        batch_id: UUID | None = None,
        touch: bool = False,
    ) -> int:
        """Allocate sequences and persist a whole batch, or roll back all of it."""
        try:
            if touch:
                await session.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(last_activity_at=datetime.now(UTC))
                )
            if messages:
                batch = MessageBatch(conversation_id=conversation_id, direction=direction)
                if batch_id is not None:
                    batch.id = batch_id
                session.add(batch)
                await session.flush()
                first = await ConversationRepository().allocate_sequence_numbers(
                    session, conversation_id, len(messages)
                )
                session.add_all(
                    [
                        Message(
                            conversation_id=conversation_id,
                            batch_id=batch.id,
                            sequence_number=first + index,
                            direction=direction,
                            text=data.text,
                            message_type=data.message_type,
                        )
                        for index, data in enumerate(messages)
                    ]
                )
                last = first + len(messages) - 1
            else:
                last = (
                    await session.execute(
                        select(Conversation.last_sequence_number).where(
                            Conversation.id == conversation_id
                        )
                    )
                ).scalar_one()
            await session.commit()
            return last
        except Exception:
            await session.rollback()
            raise


class MessageRepository(BaseRepository[Message]):
    def __init__(self) -> None:
        super().__init__(Message)

    async def get_last_messages(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        limit: int = 50,
    ) -> list[HistoryMessage]:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.desc())
            .limit(limit)
        )
        return [_message(row) for row in reversed(list(result.scalars().all()))]

    async def get_message_count(self, session: AsyncSession, conversation_id: UUID) -> int:
        result = await session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar() or 0

    async def get_after_checkpoint(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        checkpoint: int,
    ) -> list[HistoryMessage]:
        result = await session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sequence_number > checkpoint,
            )
            .order_by(Message.sequence_number.asc())
        )
        return [_message(row) for row in result.scalars().all()]

    async def get_between_inclusive(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        seq_from: int,
        seq_to: int,
    ) -> list[HistoryMessage]:
        result = await session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sequence_number >= seq_from,
                Message.sequence_number <= seq_to,
            )
            .order_by(Message.sequence_number.asc())
        )
        return [_message(row) for row in result.scalars().all()]

    async def delete_for_conversation(self, session: AsyncSession, conversation_id: UUID) -> None:
        await session.execute(delete(Message).where(Message.conversation_id == conversation_id))
        await session.flush()


class SummaryStateRepository(BaseRepository[SummaryState]):
    def __init__(self) -> None:
        super().__init__(SummaryState)

    async def _get_row(self, session: AsyncSession, conversation_id: UUID) -> SummaryState | None:
        result = await session.execute(
            select(SummaryState).where(SummaryState.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_conversation_id(
        self, session: AsyncSession, conversation_id: UUID
    ) -> RollingSummary | None:
        row = await self._get_row(session, conversation_id)
        return (
            RollingSummary(row.current_summary, row.checkpoint, row.cluster_checkpoint)
            if row
            else None
        )

    async def reset_for_conversation(self, session: AsyncSession, conversation_id: UUID) -> None:
        await session.execute(
            update(SummaryState)
            .where(SummaryState.conversation_id == conversation_id)
            .values(current_summary=None, checkpoint=0, cluster_checkpoint=0)
        )
        await session.flush()

    async def upsert(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        current_summary: str | None,
        checkpoint: int,
    ) -> SummaryState:
        existing = await self._get_row(session, conversation_id)
        data = {"current_summary": current_summary, "checkpoint": checkpoint}
        if existing:
            return await self.update(session, existing, data)
        return await self.create(session, {"conversation_id": conversation_id, **data})

    async def upsert_cluster_checkpoint(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        cluster_checkpoint: int,
    ) -> SummaryState:
        existing = await self._get_row(session, conversation_id)
        if existing:
            return await self.update(session, existing, {"cluster_checkpoint": cluster_checkpoint})
        return await self.create(
            session,
            {
                "conversation_id": conversation_id,
                "current_summary": None,
                "checkpoint": 0,
                "cluster_checkpoint": cluster_checkpoint,
            },
        )


class VectorRecordRepository(BaseRepository[VectorRecord]):
    def __init__(self) -> None:
        super().__init__(VectorRecord)

    async def get_topic(self, session: AsyncSession, topic_id: UUID) -> IndexedTopic | None:
        row = await self.get_by_id(session, topic_id)
        return _topic(row) if row is not None else None

    async def store_indexed_window(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        records: list[IndexedTopic],
        checkpoint: int,
    ) -> None:
        """Persist a complete index window and its checkpoint in one transaction."""
        try:
            session.add_all(
                [
                    VectorRecord(
                        id=record.id,
                        conversation_id=conversation_id,
                        text=record.text,
                        embedding=record.embedding,
                        kind=record.kind,
                        seq_from=record.seq_from,
                        seq_to=record.seq_to,
                        partial=record.partial,
                        created_at=record.created_at,
                    )
                    for record in records
                ]
            )
            state = await SummaryStateRepository()._get_row(session, conversation_id)
            if state is None:
                session.add(
                    SummaryState(conversation_id=conversation_id, cluster_checkpoint=checkpoint)
                )
            else:
                state.cluster_checkpoint = checkpoint
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def list_for_conversation(
        self, session: AsyncSession, conversation_id: UUID
    ) -> list[IndexedTopic]:
        result = await session.execute(
            select(VectorRecord)
            .where(VectorRecord.conversation_id == conversation_id)
            .order_by(VectorRecord.created_at.asc())
        )
        return [_topic(row) for row in result.scalars().all()]

    async def search_similar(
        self,
        session: AsyncSession,
        conversation_id: UUID | None,
        query_embedding: list[float],
        top_k: int = 10,
        *,
        kind: str = "topic",
    ) -> list[IndexedTopic]:
        dialect = session.bind.dialect.name if session.bind is not None else ""
        want = "reference" if kind == "reference" else "topic"
        filters = [
            VectorRecord.embedding.is_not(None),
            VectorRecord.kind == want,
        ]
        if conversation_id is not None:
            filters.append(VectorRecord.conversation_id == conversation_id)
        if dialect == "postgresql":
            result = await session.execute(
                select(VectorRecord)
                .where(*filters)
                .order_by(VectorRecord.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            return [_topic(row) for row in result.scalars().all()]

        result = await session.execute(select(VectorRecord).where(*filters))
        rows = list(result.scalars().all())
        scored: list[tuple[float, VectorRecord]] = []
        for row in rows:
            if row.embedding is None:
                continue
            dist = _cosine_distance(query_embedding, row.embedding)
            if dist is None:
                continue
            scored.append((dist, row))
        scored.sort(key=lambda item: item[0])
        return [_topic(row) for _, row in scored[:top_k]]

    async def delete_for_conversation(self, session: AsyncSession, conversation_id: UUID) -> None:
        await session.execute(
            delete(VectorRecord).where(VectorRecord.conversation_id == conversation_id)
        )
        await session.flush()
