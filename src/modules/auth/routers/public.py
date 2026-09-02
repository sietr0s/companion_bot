"""Публичные роуты модуля auth."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.routers import create_crud_router
from src.core.dependencies import get_current_user, get_db_session
from src.modules.auth.dependencies import get_auth_service
from src.modules.auth.schemas.public import (
    AuthAccountCreate,
    AuthAccountRead,
    AuthAccountUpdate,
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
    await auth_service.delete_account(session, auth_id)


router.include_router(
    create_crud_router(
        get_service=get_auth_service,
        create_schema=AuthAccountCreate,
        update_schema=AuthAccountUpdate,
        response_schema=AuthAccountRead,
        prefix="/accounts",
        tags=["Auth Accounts"],
        entity_name="Auth",
    )
)
