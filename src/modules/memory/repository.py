"""Memory module SQLAlchemy repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.memory.models import (
    Conversation,
    Message,
    SummaryState,
    VectorRecord,
)


class MemoryRepository:
    """Repository for memory-related database operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_or_create_conversation(
        self,
        telegram_chat_id: int,
        user_id: UUID,
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        result = await self._session.execute(
            select(Conversation).where(Conversation.telegram_chat_id == telegram_chat_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                telegram_chat_id=telegram_chat_id,
                user_id=user_id,
            )
            self._session.add(conversation)
            await self._session.flush()

        return conversation

    async def get_conversation_by_id(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        """Get conversation by ID."""
        result = await self._session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_conversation_by_telegram_id(
        self,
        telegram_chat_id: int,
    ) -> Conversation | None:
        """Get conversation by Telegram chat ID."""
        result = await self._session.execute(
            select(Conversation).where(Conversation.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()

    async def save_messages(
        self,
        conversation_id: UUID,
        messages_data: list[dict],
    ) -> list[Message]:
        """Save multiple messages to a conversation."""
        messages = []
        for msg_data in messages_data:
            message = Message(
                conversation_id=conversation_id,
                **msg_data,
            )
            self._session.add(message)
            messages.append(message)

        await self._session.flush()
        return messages

    async def update_conversation_activity(
        self,
        conversation_id: UUID,
        sequence_number: int,
    ) -> None:
        """Update conversation last activity and sequence number."""
        result = await self._session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one()
        conversation.last_sequence_number = sequence_number
        conversation.last_activity_at = datetime.utcnow()

    async def get_last_messages(
        self,
        conversation_id: UUID,
        limit: int = 50,
    ) -> list[Message]:
        """Get last N messages from conversation."""
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))

    async def get_summary_state(
        self,
        conversation_id: UUID,
    ) -> SummaryState | None:
        """Get summary state for conversation."""
        result = await self._session.execute(
            select(SummaryState).where(SummaryState.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def upsert_summary_state(
        self,
        conversation_id: UUID,
        current_summary: str | None,
        checkpoint: int,
    ) -> SummaryState:
        """Create or update summary state."""
        result = await self._session.execute(
            select(SummaryState).where(SummaryState.conversation_id == conversation_id)
        )
        summary_state = result.scalar_one_or_none()

        if not summary_state:
            summary_state = SummaryState(
                conversation_id=conversation_id,
                current_summary=current_summary,
                checkpoint=checkpoint,
            )
            self._session.add(summary_state)
        else:
            summary_state.current_summary = current_summary
            summary_state.checkpoint = checkpoint
            summary_state.updated_at = datetime.utcnow()

        await self._session.flush()
        return summary_state

    async def add_vector_record(
        self,
        conversation_id: UUID,
        text: str,
        embedding: list[float] | None = None,
        metadata: dict | None = None,
    ) -> VectorRecord:
        """Add vector record for semantic search."""
        vector_record = VectorRecord(
            conversation_id=conversation_id,
            text=text,
            embedding=embedding,
            metadata=metadata or {},
        )
        self._session.add(vector_record)
        await self._session.flush()
        return vector_record

    async def search_similar_vectors(
        self,
        conversation_id: UUID,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[VectorRecord]:
        """Search similar vectors using pgvector."""
        # This requires pgvector extension
        result = await self._session.execute(
            select(VectorRecord)
            .where(VectorRecord.conversation_id == conversation_id)
            .order_by(VectorRecord.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def get_message_count(
        self,
        conversation_id: UUID,
    ) -> int:
        """Get total message count in conversation."""
        result = await self._session.execute(
            select(func.count()).select_from(Message).where(
                Message.conversation_id == conversation_id
            )
        )
        return result.scalar() or 0
