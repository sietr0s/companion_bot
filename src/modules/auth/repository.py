"""
Репозиторий авторизации.

Расширяет BaseRepository специфичным запросом get_by_identifier.
При выносе модуля auth в микросервис — единственный файл,
требующий замены (на HTTP-клиент к другому сервису).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.auth.models import Auth


class AuthRepository(BaseRepository[Auth]):
    """Репозиторий для работы с учётными записями авторизации."""

    def __init__(self) -> None:
        super().__init__(Auth)

    async def get_by_identifier(self, session: AsyncSession, identifier: str) -> Auth | None:
        """Найти учётную запись по identifier (email или phone). Используется при логине."""
        stmt = select(Auth).where(Auth.identifier == identifier)
        result = await session.execute(stmt)
        return result.scalars().first()
