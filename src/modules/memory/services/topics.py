"""Read persisted topics for the admin API; no AI or bus dependency."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.modules.memory.models import VectorRecord
from src.modules.memory.repository import (
    MessageRepository,
    VectorRecordRepository,
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


class TopicQueryService:
    def __init__(self, vectors: VectorRecordRepository, messages: MessageRepository) -> None:
        self._vectors = vectors
        self._messages = messages

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
