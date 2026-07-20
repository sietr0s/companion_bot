"""
Базовый сервис — проксирующий слой над репозиторием.

Сервис содержит бизнес-логику и делегирует персистентность
репозиторию. При выносе модуля в микросервис сервис остаётся
без изменений — меняется только реализация репозитория.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.model import BaseModel
from src.base.repository import BaseRepository
from src.core.exceptions import NotFoundError

# Тип репозитория, с которым работает сервис
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseService(Generic[RepositoryType, ModelType]):
    """
    Дженерик-сервис, проксирующий вызовы к репозиторию.

    Конкретные сервисы расширяют его специфичными методами
    бизнес-логики (например, register, login).
    """

    def __init__(self, repository: RepositoryType):
        self.repository = repository

    async def get_by_id(
        self,
        session: AsyncSession,
        entity_id: UUID,
    ) -> ModelType | None:
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
        order_by: str | None = "-created_at",
    ) -> Sequence[ModelType]:
        """
        Получить список сущностей.

        Args:
            session: SQLAlchemy async session
            skip: Пропуск первых N сущностей
            limit: Максимальное количество сущностей

        Returns:
            Список сущностей
        """
        return await self.repository.get_all(session, skip, limit, order_by)

    async def create(
        self,
        session: AsyncSession,
        data: dict[str, Any],
    ) -> ModelType:
        """
        Создать сущность.

        Args:
            session: SQLAlchemy async session
            data: Данные для создания

        Returns:
            Созданная сущность
        """
        return await self.repository.create(session, data)

    async def update(
        self,
        session: AsyncSession,
        obj_id: UUID,
        data: dict[str, Any],
    ) -> ModelType:
        """
        Обновить сущность.

        Args:
            session: SQLAlchemy async session
            db_obj: Сущность для обновления
            data: Новые данные

        Returns:
            Обновлённая сущность
        """
        obj = await self.get_by_id(session, obj_id)
        if obj is None:
            raise NotFoundError()
        return await self.repository.update(session, obj, data)

    async def delete(self, session: AsyncSession, obj_id: UUID) -> None:
        """
        Удалить сущность.

        Args:
            session: SQLAlchemy async session
            db_obj: Сущность для удаления
        """
        obj = await self.get_by_id(session, obj_id)
        if obj is None:
            raise NotFoundError()
        await self.repository.delete(session, obj)
