"""
Репозиторий пользователей.

Расширяет BaseRepository специфичным запросом get_by_auth_id.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.base.repository import BaseRepository
from src.modules.users.models import Telegram, User


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с профилями пользователей."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_auth_id(self, session: AsyncSession, auth_id: uuid.UUID) -> User | None:
        """Найти профиль по ID учётной записи авторизации."""
        stmt = select(User).where(User.auth_id == auth_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_by_auth_id_with_telegram(
        self, session: AsyncSession, auth_id: uuid.UUID
    ) -> User | None:
        """Найти профиль с подгруженным Telegram по auth_id."""
        stmt = (
            select(User)
            .options(selectinload(User.telegram))
            .where(User.auth_id == auth_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class TelegramRepository(BaseRepository[Telegram]):
    """Репозиторий для работы с Telegram-аккаунтами."""

    def __init__(self) -> None:
        super().__init__(Telegram)

    async def get_by_telegram_id(self, session: AsyncSession, telegram_id: str) -> Telegram | None:
        """Найти Telegram-аккаунт по telegram_id."""
        stmt = select(Telegram).where(Telegram.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_auth_id(self, session: AsyncSession, auth_id: uuid.UUID) -> Telegram | None:
        """Найти Telegram-аккаунт по auth_id (через User)."""
        stmt = (
            select(Telegram)
            .join(User, User.telegram_id == Telegram.id)
            .where(User.auth_id == auth_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list_with_profiles(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Telegram]:
        """Получить список Telegram-аккаунтов с профилями."""
        stmt = (
            select(Telegram)
            .join(User, User.telegram_id == Telegram.id, isouter=True)
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
