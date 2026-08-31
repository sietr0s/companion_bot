"""Memory module repositories."""

import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.memory.models import Conversation, Message, SummaryState, VectorRecord


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

    async def get_by_telegram_chat_id(
        self, session: AsyncSession, telegram_chat_id: int
    ) -> Conversation | None:
        result = await session.execute(
            select(Conversation).where(Conversation.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        session: AsyncSession,
        telegram_chat_id: int,
        user_id: UUID,
    ) -> Conversation:
        conversation = await self.get_by_telegram_chat_id(session, telegram_chat_id)
        if conversation:
            return conversation
        return await self.create(
            session,
            {"telegram_chat_id": telegram_chat_id, "user_id": user_id},
        )


class MessageRepository(BaseRepository[Message]):
    def __init__(self) -> None:
        super().__init__(Message)

    async def get_last_messages(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        limit: int = 50,
    ) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.desc())
            .limit(limit)
        )
        return list(reversed(list(result.scalars().all())))

    async def get_message_count(self, session: AsyncSession, conversation_id: UUID) -> int:
        result = await session.execute(
            select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
        )
        return result.scalar() or 0

    async def get_after_checkpoint(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        checkpoint: int,
    ) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sequence_number > checkpoint,
            )
            .order_by(Message.sequence_number.asc())
        )
        return list(result.scalars().all())


class SummaryStateRepository(BaseRepository[SummaryState]):
    def __init__(self) -> None:
        super().__init__(SummaryState)

    async def get_by_conversation_id(
        self, session: AsyncSession, conversation_id: UUID
    ) -> SummaryState | None:
        result = await session.execute(
            select(SummaryState).where(SummaryState.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        current_summary: str | None,
        checkpoint: int,
    ) -> SummaryState:
        existing = await self.get_by_conversation_id(session, conversation_id)
        data = {"current_summary": current_summary, "checkpoint": checkpoint}
        if existing:
            return await self.update(session, existing, data)
        return await self.create(session, {"conversation_id": conversation_id, **data})


class VectorRecordRepository(BaseRepository[VectorRecord]):
    def __init__(self) -> None:
        super().__init__(VectorRecord)

    async def search_similar(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[VectorRecord]:
        dialect = session.bind.dialect.name if session.bind is not None else ""
        if dialect == "postgresql":
            result = await session.execute(
                select(VectorRecord)
                .where(
                    VectorRecord.conversation_id == conversation_id,
                    VectorRecord.embedding.is_not(None),
                )
                .order_by(VectorRecord.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            return list(result.scalars().all())

        result = await session.execute(
            select(VectorRecord).where(
                VectorRecord.conversation_id == conversation_id,
                VectorRecord.embedding.is_not(None),
            )
        )
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
        return [row for _, row in scored[:top_k]]
