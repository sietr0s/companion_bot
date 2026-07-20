"""
Внутренние роуты модуля auth.

Доступны только внутри кластера (network-level).
Без JWT-авторизации — доступ ограничивается
Docker network / k8s NetworkPolicy.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.core.internal_auth import require_internal_service_key
from src.modules.auth.dependencies import get_auth_service
from src.modules.auth.schemas.internal import (
    AuthCreate,
    AuthRead,
    AuthUpdate,
    VerifyTokenRequest,
    VerifyTokenResponse,
)
from src.modules.auth.service import AuthService

router = APIRouter(
    prefix="/internal/auth",
    tags=["Internal"],
    dependencies=[Depends(require_internal_service_key)],
)


@router.post(
    "/",
    response_model=AuthRead,
    status_code=status.HTTP_201_CREATED,
    summary="[Internal] Создать учётную запись",
)
async def create_account(
    data: AuthCreate,
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> AuthRead:
    """Создать учётную запись (internal, без JWT)."""
    return await service.create_account(session, data.model_dump())


@router.get(
    "/{auth_id}",
    response_model=AuthRead,
    summary="[Internal] Получить учётную запись по auth_id",
)
async def get_account(
    auth_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> AuthRead:
    """Получить учётную запись по auth_id (internal)."""
    return await service.get_by_id(session, auth_id)


@router.patch(
    "/{auth_id}",
    response_model=AuthRead,
    summary="[Internal] Обновить учётную запись",
)
async def update_account(
    auth_id: uuid.UUID,
    data: AuthUpdate,
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> AuthRead:
    """Обновить учётную запись (internal)."""
    return await service.update_account(session, auth_id, data.model_dump(exclude_unset=True))


@router.delete(
    "/{auth_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Internal] Удалить учётную запись",
)
async def delete_account(
    auth_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> None:
    """Удалить учётную запись (internal, без проверки пароля)."""
    await service.delete_account_internal(session, auth_id)


@router.post(
    "/verify",
    response_model=VerifyTokenResponse,
    summary="[Internal] Проверить валидность токена",
)
async def verify_token(
    data: VerifyTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> VerifyTokenResponse:
    """Проверить валидность JWT токена (internal)."""
    return await service.verify_token_internal(data.token)
