"""Batching module repositories."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.batching.models import Batch, BatchMessage


class BatchRepository(BaseRepository[Batch]):
    def __init__(self) -> None:
        super().__init__(Batch)

    async def get_pending_batch(self, session: AsyncSession, telegram_chat_id: int) -> Batch | None:
        stmt = (
            select(Batch)
            .where(Batch.telegram_chat_id == telegram_chat_id, Batch.status == "pending")
            .order_by(Batch.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().first()


class BatchMessageRepository(BaseRepository[BatchMessage]):
    def __init__(self) -> None:
        super().__init__(BatchMessage)

    async def get_by_batch_id(self, session: AsyncSession, batch_id) -> list[BatchMessage]:
        stmt = (
            select(BatchMessage)
            .where(BatchMessage.batch_id == batch_id)
            .order_by(BatchMessage.sequence_number)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
