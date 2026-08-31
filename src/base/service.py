"""
Базовый сервис — проксирующий слой над репозиторием.

Сервис содержит бизнес-логику и делегирует персистентность
репозиторию. SQL и ORM здесь не используются.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel as PydanticModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter
from src.base.model import BaseModel
from src.base.repository import BaseRepository
from src.core.exceptions import NotFoundError

RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseService(Generic[RepositoryType, ModelType]):
    """Дженерик-сервис с CRUD, делегируемым репозиторию."""

    def __init__(self, repository: RepositoryType):
        self.repository = repository

    async def get_by_id(
        self,
        session: AsyncSession,
        entity_id: UUID,
    ) -> ModelType | None:
        return await self.repository.get_by_id(session, entity_id)

    async def get_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "-created_at",
    ) -> Sequence[ModelType]:
        return await self.repository.get_all(session, skip, limit, order_by)

    async def get_list(
        self,
        session: AsyncSession,
        filters: list[Filter] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "-created_at",
    ) -> tuple[Sequence[ModelType], int]:
        return await self.repository.get_list(session, filters, skip, limit, order_by)

    async def create(
        self,
        session: AsyncSession,
        data: dict[str, Any] | PydanticModel,
    ) -> ModelType:
        payload = data.model_dump(exclude_unset=True) if isinstance(data, PydanticModel) else data
        return await self.repository.create(session, payload)

    async def update(
        self,
        session: AsyncSession,
        obj_id: UUID,
        data: dict[str, Any] | PydanticModel,
    ) -> ModelType:
        obj = await self.get_by_id(session, obj_id)
        if obj is None:
            raise NotFoundError()
        payload = data.model_dump(exclude_unset=True) if isinstance(data, PydanticModel) else data
        return await self.repository.update(session, obj, payload)

    async def delete(self, session: AsyncSession, obj_id: UUID) -> None:
        obj = await self.get_by_id(session, obj_id)
        if obj is None:
            raise NotFoundError()
        await self.repository.delete(session, obj)
