"""Репозиторий собеседников Telegram."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.users.models import User


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_telegram_id(self, session: AsyncSession, telegram_id: int) -> User | None:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
