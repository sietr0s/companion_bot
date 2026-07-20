"""Публичные роуты модуля classifier.

HTTP API для CRUD категорий.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_admin, get_db_session
from src.modules.classifier.dependencies import get_classifier_service
from src.modules.classifier.schemas.public.category import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)
from src.modules.classifier.service import ClassifierService

router = APIRouter(prefix="/api/v1/public/classifier", tags=["Classifier"])


@router.post(
    "/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать категорию",
)
async def create_category(
    data: CategoryCreate,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: ClassifierService = Depends(get_classifier_service),
) -> CategoryRead:
    """Создать новую категорию для классификации."""
    return await service.create_category(session, data)


@router.get(
    "/categories",
    response_model=list[CategoryRead],
    summary="Список категорий",
)
async def get_categories(
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    session: AsyncSession = Depends(get_db_session),
    service: ClassifierService = Depends(get_classifier_service),
) -> list[CategoryRead]:
    """Получить список всех категорий."""
    categories, _ = await service.get_all_categories(session, order_by=order_by)
    return categories


@router.patch(
    "/categories/{slug}",
    response_model=CategoryRead,
    summary="Обновить категорию",
)
async def update_category(
    slug: str,
    data: CategoryUpdate,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: ClassifierService = Depends(get_classifier_service),
) -> CategoryRead:
    """Обновить категорию по slug."""
    return await service.update_category(session, slug, data)


@router.delete(
    "/categories/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить категорию",
)
async def delete_category(
    slug: str,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: ClassifierService = Depends(get_classifier_service),
) -> None:
    """Удалить категорию по slug."""
    await service.delete_category(session, slug)
