"""
Базовый сервис — проксирующий слой над репозиторием.

Сервис содержит бизнес-логику и делегирует персистентность
репозиторию. При выносе модуля в микросервис сервис остаётся
без изменений — меняется только реализация репозитория.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.model import BaseModel
from src.base.repository import BaseRepository

# Тип репозитория, с которым работает сервис
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseService(Generic[RepositoryType]):
    """
    Дженерик-сервис, проксирующий вызовы к репозиторию.

    Конкретные сервисы расширяют его специфичными методами
    бизнес-логики (например, register, login).
    """

    def __init__(self, repository: RepositoryType):
        self.repository = repository

    async def get_by_id(self, session: AsyncSession, entity_id: Any) -> Any | None:
        """
        Получить сущность по ID.

        Args:
            session: SQLAlchemy async session
            entity_id: ID сущности

        Returns:
            Сущность или None, если не найдена
        """
        return await self.repository.get_by_id(session, entity_id)

    async def get_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Any]:
        """
        Получить список сущностей.

        Args:
            session: SQLAlchemy async session
            skip: Пропуск первых N сущностей
            limit: Максимальное количество сущностей

        Returns:
            Список сущностей
        """
        return await self.repository.get_all(session, skip, limit)

    async def create(self, session: AsyncSession, data: dict[str, Any]) -> Any:
        """
        Создать сущность.

        Args:
            session: SQLAlchemy async session
            data: Данные для создания

        Returns:
            Созданная сущность
        """
        return await self.repository.create(session, data)

    async def update(self, session: AsyncSession, db_obj: Any, data: dict[str, Any]) -> Any:
        """
        Обновить сущность.

        Args:
            session: SQLAlchemy async session
            db_obj: Сущность для обновления
            data: Новые данные

        Returns:
            Обновлённая сущность
        """
        return await self.repository.update(session, db_obj, data)

    async def delete(self, session: AsyncSession, db_obj: Any) -> None:
        """
        Удалить сущность.

        Args:
            session: SQLAlchemy async session
            db_obj: Сущность для удаления
        """
        return await self.repository.delete(session, db_obj)
