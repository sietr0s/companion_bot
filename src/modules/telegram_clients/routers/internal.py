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
from src.modules.telegram_clients.service import TelegramClientService

router = APIRouter()


@router.get(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    status_code=status.HTTP_200_OK,
)
async def get_settings(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Получить настройки Telegram-аккаунта."""
    settings = await service.get_settings(session, account_id)
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
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Создать настройки Telegram-аккаунта."""
    settings = await service._create_default_settings(session, account_id)
    # Если переданы кастомные значения - обновляем
    if data.model_dump(exclude_unset=True):
        settings = await service.update_settings(
            session, account_id, data.model_dump(exclude_unset=True)
        )
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
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Обновить настройки Telegram-аккаунта."""
    settings = await service.update_settings(
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
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> None:
    """Удалить настройки Telegram-аккаунта."""
    await service.delete_settings(session, account_id)
