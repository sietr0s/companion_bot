"""
Публичные роуты модуля auth.

POST /api/v1/public/auth/register, /api/v1/public/auth/login — регистрация и вход.
PATCH /api/v1/public/auth/me/password, DELETE /api/v1/public/auth/me — требуют JWT.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user, get_db_session
from src.modules.auth.dependencies import get_auth_service
from src.modules.auth.schemas_api import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.modules.auth.service import AuthService

router = APIRouter(prefix="/api/v1/public/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Регистрация: создаёт учётную запись авторизации и возвращает JWT.

    Профиль пользователя создаётся отдельным запросом POST /users/.
    """
    return await auth_service.register(session, data.model_dump())


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Авторизация пользователя",
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Авторизация: проверяет email/пароль и возвращает JWT-токен."""
    return await auth_service.login(session, data.model_dump())


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Смена пароля",
)
async def change_password(
    data: ChangePasswordRequest,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Сменить пароль текущего пользователя."""
    await auth_service.change_password(session, auth_id, data.current_password, data.new_password)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление учётной записи",
)
async def delete_account(
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Удалить учётную запись текущего пользователя (каскадное удаление профиля).

    Без пароля — удаление по JWT (auth_id)."""
    await auth_service.delete_account(session, auth_id)
