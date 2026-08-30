"""
Внутренние роуты модуля users.

Доступны только внутри кластера (network-level).
Без JWT-авторизации — доступ ограничивается
Docker network / k8s NetworkPolicy.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.core.internal_auth import require_internal_service_key
from src.modules.users.dependencies import get_user_service
from src.modules.users.schemas_api import (
    TelegramCreate,
    TelegramRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from src.modules.users.service import UserService

router = APIRouter(
    prefix="/internal/users",
    tags=["Internal"],
    dependencies=[Depends(require_internal_service_key)],
)

FILTER_FIELDS = {
    "id",
    "auth_id",
    "first_name",
    "last_name",
    "telegram_id",
    "created_at",
    "updated_at",
}


@router.get(
    "/",
    response_model=PaginatedResponse[UserRead],
    summary="[Internal] Получить пользователей с фильтрацией",
)
async def get_users(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> PaginatedResponse:
    """
    Внутренний эндпоинт для межмодульного взаимодействия.

    Фильтры: `filters=field+eq+value`.
    Операторы: eq, ne, gt, ge, lt, le, like, ilike, in.
    """
    parsed = parse_filters(filters, allowed_fields=FILTER_FIELDS)
    skip = (page - 1) * limit
    users, total = await user_service.get_users(session, parsed, skip, limit, order_by)
    return PaginatedResponse.from_list(users, total, page=page, page_size=limit)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="[Internal] Создать профиль пользователя",
)
async def create_profile_internal(
    data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Создать профиль пользователя (internal, без JWT)."""
    await user_service.create_user_profile(
        session, data.auth_id, data.model_dump(exclude_unset=True)
    )
    return await user_service.get_profile(session, data.auth_id)


@router.get(
    "/{profile_id}",
    response_model=UserRead,
    summary="[Internal] Получить профиль по id",
)
async def get_profile_internal(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Получить профиль по id (internal)."""
    profile = await user_service.get_by_id(session, profile_id)
    if not profile:
        raise NotFoundError(detail="Профиль не найден")
    return profile


@router.patch(
    "/{profile_id}",
    response_model=UserRead,
    summary="[Internal] Обновить профиль",
)
async def update_profile_internal(
    profile_id: uuid.UUID,
    data: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Обновить профиль (internal)."""
    profile = await user_service.get_by_id(session, profile_id)
    if not profile:
        raise NotFoundError(detail="Профиль не найден")
    return await user_service.update(session, profile.id, data.model_dump(exclude_unset=True))


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Internal] Удалить профиль",
)
async def delete_profile_internal(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> None:
    """Удалить профиль (internal, без проверки JWT)."""
    profile = await user_service.get_by_id(session, profile_id)
    if not profile:
        raise NotFoundError(detail="Профиль не найден")
    await user_service.delete(session, profile.id)


@router.post(
    "/{profile_id}/telegram",
    response_model=TelegramRead,
    status_code=status.HTTP_201_CREATED,
    summary="[Internal] Создать Telegram профиль",
)
async def create_telegram_profile(
    profile_id: uuid.UUID,
    data: TelegramCreate,
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> TelegramRead:
    """Создать Telegram профиль и связать с пользователем (internal)."""
    return await user_service.create_telegram_profile(session, profile_id, data.model_dump())
