"""Внутренние роуты модуля classifier.

Доступны только внутри кластера (network-level).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.modules.classifier.dependencies import get_classifier_service
from src.modules.classifier.schemas.public.category import CategoryRead
from src.modules.classifier.service import ClassifierService

router = APIRouter(prefix="/internal/classifier")


@router.get(
    "/categories",
    response_model=list[CategoryRead],
    summary="[Internal] Список категорий",
)
async def get_categories(
    session: AsyncSession = Depends(get_db_session),
    service: ClassifierService = Depends(get_classifier_service),
) -> list[CategoryRead]:
    """Получить список всех категорий для внутреннего использования."""
    categories, _ = await service.get_all_categories(session)
    return categories
