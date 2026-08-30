"""
Публичные роуты модуля пользователей.

auth_id извлекается из JWT-токена.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import (
    get_current_admin,
    get_current_user,
    get_db_session,
)
from src.core.exceptions import NotFoundError
from src.modules.users.dependencies import get_user_service
from src.modules.users.schemas_api import TelegramRead, UserCreate, UserRead, UserUpdate
from src.modules.users.service import UserService

router = APIRouter(prefix="/api/v1/public/users", tags=["Users"])

ADMIN_FILTER_FIELDS = {
    "id",
    "auth_id",
    "first_name",
    "last_name",
    "created_at",
    "updated_at",
}


@router.get(
    "/",
    response_model=PaginatedResponse[UserRead],
    summary="Получить пользователей для администратора",
)
async def get_users_admin(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    _admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserRead]:
    """Вернуть список профилей только авторизованному администратору."""
    parsed = parse_filters(filters, allowed_fields=ADMIN_FILTER_FIELDS)
    users, total = await user_service.get_users(
        session,
        filters=parsed,
        skip=(page - 1) * limit,
        limit=limit,
        order_by=order_by,
    )
    return PaginatedResponse.from_list(users, total, page=page, page_size=limit)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создание профиля пользователя",
)
async def create_profile(
    data: UserCreate,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """
    Создаёт профиль пользователя.

    auth_id берётся из JWT-токена (авторизованный пользователь).
    В теле запроса можно передать first_name, last_name и т.д.
    """
    await user_service.create_user_profile(session, auth_id, data.model_dump(exclude_unset=True))
    profile = await user_service.get_profile(session, auth_id)
    return profile


@router.get(
    "/me",
    response_model=UserRead,
    summary="Получение профиля текущего пользователя",
)
async def get_me(
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Возвращает профиль авторизованного пользователя."""
    profile = await user_service.get_profile(session, auth_id)
    return profile


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Обновление профиля текущего пользователя",
)
async def update_me(
    data: UserUpdate,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Обновляет профиль авторизованного пользователя (partial update)."""
    profile = await user_service.update_profile(
        session, auth_id, data.model_dump(exclude_unset=True)
    )
    return profile


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление профиля текущего пользователя",
)
async def delete_me(
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> None:
    """Удаляет профиль авторизованного пользователя."""
    await user_service.delete_profile(session, auth_id)


@router.get(
    "/me/telegram",
    response_model=TelegramRead,
    summary="Получить Telegram профиль текущего пользователя",
)
async def get_my_telegram(
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> TelegramRead:
    """Получить связанный Telegram профиль текущего пользователя."""
    telegram = await user_service.get_telegram_by_auth_id(session, auth_id)
    if not telegram:
        raise NotFoundError(detail="Telegram профиль не найден")
    return telegram


@router.patch(
    "/{profile_id}",
    response_model=UserRead,
    summary="Обновить пользователя администратором",
)
async def update_user_admin(
    profile_id: uuid.UUID,
    data: UserUpdate,
    _admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Обновить профиль пользователя из административного интерфейса."""
    profile = await user_service.get_by_id(session, profile_id)
    if profile is None:
        raise NotFoundError(detail="Профиль пользователя не найден")
    return await user_service.update_profile(
        session,
        profile.auth_id,
        data.model_dump(exclude_unset=True),
    )
