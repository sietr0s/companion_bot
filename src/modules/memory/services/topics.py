"""Read indexed topic domain entities; HTTP serialization belongs to contracts/routes."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.modules.memory.domain import IndexedTopic, TopicHistory
from src.modules.memory.repository import MessageRepository, VectorRecordRepository


class TopicQueryService:
    def __init__(self, vectors: VectorRecordRepository, messages: MessageRepository) -> None:
        self._vectors = vectors
        self._messages = messages

    async def list_topics(self, session: AsyncSession, conversation_id: UUID) -> list[IndexedTopic]:
        return sorted(
            await self._vectors.list_for_conversation(session, conversation_id),
            key=lambda topic: topic.seq_from,
        )

    async def get_topic(
        self, session: AsyncSession, conversation_id: UUID, topic_id: UUID
    ) -> TopicHistory:
        topic = await self._vectors.get_topic(session, topic_id)
        if topic is None or topic.conversation_id != conversation_id:
            raise NotFoundError(detail="Тема не найдена")
        messages = await self._messages.get_between_inclusive(
            session, conversation_id, topic.seq_from, topic.seq_to
        )
        return TopicHistory(topic, messages)
