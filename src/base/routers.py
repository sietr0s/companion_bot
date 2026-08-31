"""
Фабрика CRUD-роутера для FastAPI.

Стандартные endpoints:
- GET / — список с пагинацией
- GET /{item_id} — по ID
- POST / — создание
- PUT /{item_id} — обновление
- DELETE /{item_id} — удаление

Роутер вызывает только сервис, без SQL и без прямого доступа к репозиторию.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel as PydanticModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.schemas import PaginatedResponse
from src.base.service import BaseService
from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError


def create_crud_router(
    *,
    get_service: Callable[..., BaseService],
    create_schema: type[PydanticModel],
    update_schema: type[PydanticModel],
    response_schema: type[PydanticModel],
    prefix: str,
    tags: list[str],
    entity_name: str = "Entity",
) -> APIRouter:
    """Собрать CRUD APIRouter с DI сервиса и сессии."""
    router = APIRouter(prefix=prefix, tags=tags)

    @router.get("/", response_model=PaginatedResponse[response_schema])
    async def get_list(
        session: AsyncSession = Depends(get_db_session),
        service: BaseService = Depends(get_service),
        page: int = Query(1, ge=1),
        page_size: int = Query(100, ge=1, le=1000),
        order_by: str | None = Query("-created_at"),
    ) -> Any:
        skip = (page - 1) * page_size
        items, total = await service.get_list(
            session,
            skip=skip,
            limit=page_size,
            order_by=order_by,
        )
        return PaginatedResponse.from_list(
            items=[response_schema.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    @router.get("/{item_id}", response_model=response_schema)
    async def get_by_id(
        item_id: UUID,
        session: AsyncSession = Depends(get_db_session),
        service: BaseService = Depends(get_service),
    ) -> Any:
        item = await service.get_by_id(session, item_id)
        if item is None:
            raise NotFoundError(detail=f"{entity_name} с ID {item_id} не найден")
        return response_schema.model_validate(item)

    @router.post("/", response_model=response_schema, status_code=status.HTTP_201_CREATED)
    async def create(
        data: create_schema,  # type: ignore[valid-type]
        session: AsyncSession = Depends(get_db_session),
        service: BaseService = Depends(get_service),
    ) -> Any:
        created = await service.create(session, data)
        return response_schema.model_validate(created)

    @router.put("/{item_id}", response_model=response_schema)
    async def update(
        item_id: UUID,
        data: update_schema,  # type: ignore[valid-type]
        session: AsyncSession = Depends(get_db_session),
        service: BaseService = Depends(get_service),
    ) -> Any:
        updated = await service.update(session, item_id, data)
        return response_schema.model_validate(updated)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete(
        item_id: UUID,
        session: AsyncSession = Depends(get_db_session),
        service: BaseService = Depends(get_service),
    ) -> None:
        await service.delete(session, item_id)

    return router
