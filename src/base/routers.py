"""
Базовый CRUD роутер для FastAPI.

Предоставляет стандартные endpoints для всех моделей:
- GET / - список с пагинацией
- GET /{id} - получение по ID
- POST / - создание
- PUT /{id} - обновление
- DELETE /{id} - удаление

Конкретные роутеры наследуются от этого класса и добавляют
специфичные endpoints (например, /register, /login).
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel as PydanticModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.model import BaseModel
from src.base.repository import BaseRepository
from src.base.schemas import PaginatedResponse
from src.base.service import BaseService
from src.core.database import get_session
from src.core.exceptions import NotFoundError

# Типы для дженерика
ModelType = TypeVar("ModelType", bound=BaseModel)
ServiceType = TypeVar("ServiceType", bound=BaseService)
CreateSchema = TypeVar("CreateSchema", bound=PydanticModel)
UpdateSchema = TypeVar("UpdateSchema", bound=PydanticModel)
ResponseSchema = TypeVar("ResponseSchema", bound=PydanticModel)


class BaseCRUDRouter(
    Generic[ModelType, ServiceType, CreateSchema, UpdateSchema, ResponseSchema],
):
    """
    Базовый CRUD роутер с пагинацией.

    Конкретные роутеры наследуются от него и указывают свои типы:
    - ModelType: SQLAlchemy модель
    - ServiceType: Сервис (наследуется от BaseService)
    - CreateSchema: Pydantic схема для создания
    - UpdateSchema: Pydantic схема для обновления
    - ResponseSchema: Pydantic схема для ответа
    """

    def __init__(
        self,
        model: type[ModelType],
        service: ServiceType,
        create_schema: type[CreateSchema],
        update_schema: type[UpdateSchema],
        response_schema: type[ResponseSchema],
        prefix: str = "",
        tags: list[str] | None = None,
    ):
        self.model = model
        self.service = service
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema

        self.router = APIRouter(prefix=prefix, tags=tags or [])
        self._register_routes()

    def _register_routes(self) -> None:
        """Регистрация CRUD routes."""
        self.router.add_api_route(
            "/",
            self.get_list,
            methods=["GET"],
            summary="Get list",
            description="Получить список сущностей с пагинацией",
        )
        self.router.add_api_route(
            "/{item_id}",
            self.get_by_id,
            methods=["GET"],
            summary="Get by ID",
            description="Получить сущность по ID",
        )
        self.router.add_api_route(
            "/",
            self.create,
            methods=["POST"],
            summary="Create",
            description="Создать новую сущность",
        )
        self.router.add_api_route(
            "/{item_id}",
            self.update,
            methods=["PUT"],
            summary="Update",
            description="Обновить сущность",
        )
        self.router.add_api_route(
            "/{item_id}",
            self.delete,
            methods=["DELETE"],
            summary="Delete",
            description="Удалить сущность",
        )

    async def get_list(
        self,
        session: AsyncSession = Depends(get_session),
        page: int = Query(1, ge=1, description="Номер страницы"),
        page_size: int = Query(100, ge=1, le=1000, description="Размер страницы"),
        order_by: str | None = Query("-created_at", description="Сортировка"),
    ) -> PaginatedResponse[ResponseSchema]:
        """
        Получить список сущностей с пагинацией.

        Args:
            page: Номер страницы (начиная с 1)
            page_size: Размер страницы (1-1000)
            order_by: Поле для сортировки (с префиксом - для убывания)

        Returns:
            PaginatedResponse со списком сущностей и мета-данными
        """
        skip = (page - 1) * page_size
        items, total = await self.service.repository.get_list(
            session=session,
            skip=skip,
            limit=page_size,
            order_by=order_by,
        )
        return PaginatedResponse.from_list(
            items=[self.response_schema.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_by_id(
        self,
        item_id: UUID,
        session: AsyncSession = Depends(get_session),
    ) -> ResponseSchema:
        """
        Получить сущность по ID.

        Args:
            item_id: UUID сущности

        Returns:
            Сущность

        Raises:
            NotFoundError: Если сущность не найдена
        """
        item = await self.service.get_by_id(session, item_id)
        if item is None:
            raise NotFoundError(detail=f"{self.model.__name__} с ID {item_id} не найден")
        return self.response_schema.model_validate(item)

    async def create(
        self,
        data: CreateSchema,
        session: AsyncSession = Depends(get_session),
    ) -> ResponseSchema:
        """
        Создать новую сущность.

        Args:
            data: Данные для создания

        Returns:
            Созданная сущность
        """
        created = await self.service.create(session, data)
        return self.response_schema.model_validate(created)

    async def update(
        self,
        item_id: UUID,
        data: UpdateSchema,
        session: AsyncSession = Depends(get_session),
    ) -> ResponseSchema:
        """
        Обновить сущность.

        Args:
            item_id: UUID сущности
            data: Новые данные

        Returns:
            Обновлённая сущность

        Raises:
            NotFoundError: Если сущность не найдена
        """
        updated = await self.service.update(session, item_id, data)
        return self.response_schema.model_validate(updated)

    async def delete(
        self,
        item_id: UUID,
        session: AsyncSession = Depends(get_session),
    ) -> None:
        """
        Удалить сущность.

        Args:
            item_id: UUID сущности

        Raises:
            NotFoundError: Если сущность не найдена
        """
        await self.service.delete(session, item_id)
