"""Internal API роуты модуля Telegram-клиентов."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.modules.telegram_clients.dependencies import get_telegram_settings_service
from src.modules.telegram_clients.schemas.internal.settings import (
    TelegramSettingsCreate,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
)
from src.modules.telegram_clients.services import TelegramAccountService, TelegramSettingsService

router = APIRouter()


@router.get(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    status_code=status.HTTP_200_OK,
)
async def get_settings(
        account_id: uuid.UUID,
        session: AsyncSession = Depends(get_db_session),
        service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Получить настройки Telegram-аккаунта."""
    settings = await service.get_by_id(session, account_id)
    return TelegramSettingsRead.model_validate(settings)


@router.post(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_settings(
        account_id: uuid.UUID,
        data: TelegramSettingsCreate,
        session: AsyncSession = Depends(get_db_session),
        service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Создать настройки Telegram-аккаунта."""
    await service.create_default_settings(session, account_id)
    settings = await service.update(session, account_id, data.model_dump(exclude_unset=True))
    return TelegramSettingsRead.model_validate(settings)


@router.put(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    status_code=status.HTTP_200_OK,
)
async def update_settings(
        account_id: uuid.UUID,
        data: TelegramSettingsUpdate,
        session: AsyncSession = Depends(get_db_session),
        service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Обновить настройки Telegram-аккаунта."""
    settings = await service.update(
        session, account_id, data.model_dump(exclude_unset=True)
    )
    return TelegramSettingsRead.model_validate(settings)


@router.delete(
    "/{account_id}/settings",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_settings(
        account_id: uuid.UUID,
        session: AsyncSession = Depends(get_db_session),
        service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> None:
    """Удалить настройки Telegram-аккаунта."""
    await service.delete(session, account_id)
