"""Telegram account reading-settings endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.dependencies import (
    get_telegram_settings_repository,
    get_telegram_settings_service,
)
from src.modules.telegram_clients.repository import TelegramSettingsRepository
from src.modules.telegram_clients.schemas.internal.settings import (
    TelegramSettingsCreate,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
)
from src.modules.telegram_clients.services import TelegramSettingsService

router = APIRouter(prefix="/{account_id}/settings")


@router.get("", response_model=TelegramSettingsRead, summary="Настройки чтения аккаунта")
async def get_settings(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    repository: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
) -> TelegramSettingsRead:
    settings = await repository.get_by_account_id(session, account_id)
    if not settings:
        raise NotFoundError(detail="Настройки не найдены")
    return TelegramSettingsRead.model_validate(settings)


@router.post("", response_model=TelegramSettingsRead, status_code=status.HTTP_201_CREATED, summary="Создать настройки чтения")
async def create_settings(
    account_id: uuid.UUID,
    data: TelegramSettingsCreate,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    await service.create_default_settings(session, account_id)
    settings = await service.update(session, account_id, data.model_dump(exclude_unset=True))
    return TelegramSettingsRead.model_validate(settings)


@router.put("", response_model=TelegramSettingsRead, summary="Обновить настройки чтения")
async def update_settings(
    account_id: uuid.UUID,
    data: TelegramSettingsUpdate,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    settings = await service.update(session, account_id, data.model_dump(exclude_unset=True))
    return TelegramSettingsRead.model_validate(settings)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить настройки чтения")
async def delete_settings(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> None:
    await service.delete(session, account_id)
