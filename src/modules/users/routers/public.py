"""
Публичные роуты модуля пользователей.

auth_id извлекается из JWT-токена.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user, get_db_session
from src.core.exceptions import NotFoundError
from src.modules.users.dependencies import get_user_service
from src.modules.users.schemas.public import TelegramRead, UserCreate, UserRead, UserUpdate
from src.modules.users.service import UserService

router = APIRouter(prefix="/api/v1/public/users")


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
