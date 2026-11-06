"""Manager routes grouped by entity; authentication is applied by the level router."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.routers import create_crud_router
from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.dependencies import (
    get_telegram_settings_repository,
    get_telegram_settings_service,
)
from src.modules.telegram_clients.repository import TelegramSettingsRepository
from src.modules.telegram_clients.schemas.api import (
    TelegramSettingsCreate,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
    WhitelistEntryCreate,
)
from src.modules.telegram_clients.services import TelegramSettingsService

router = APIRouter()


@router.get(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    summary="Настройки чтения аккаунта",
)
async def get_settings(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    repository: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
) -> TelegramSettingsRead:
    settings = await repository.get_by_account_id(session, account_id)
    if not settings:
        raise NotFoundError(detail="Настройки не найдены")
    return TelegramSettingsRead.model_validate(settings)


@router.post(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать настройки чтения",
)
async def create_settings(
    account_id: uuid.UUID,
    data: TelegramSettingsCreate,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    settings = await service.create_default_settings(session, account_id)
    payload = data.model_dump(exclude_unset=True)
    if payload:
        settings = await service.update(session, settings.id, payload)
    return TelegramSettingsRead.model_validate(settings)


@router.put(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    summary="Обновить настройки чтения",
)
async def update_settings(
    account_id: uuid.UUID,
    data: TelegramSettingsUpdate,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
    repository: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
) -> TelegramSettingsRead:
    settings_obj = await repository.get_by_account_id(session, account_id)
    if not settings_obj:
        raise NotFoundError(detail="Настройки не найдены")
    settings = await service.update(session, settings_obj.id, data.model_dump(exclude_unset=True))
    return TelegramSettingsRead.model_validate(settings)


@router.delete(
    "/{account_id}/settings",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить настройки чтения",
)
async def delete_settings(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> None:
    await service.delete(session, account_id)


@router.post("/{account_id}/whitelist", response_model=TelegramSettingsRead)
async def add_chat_to_whitelist(
    account_id: uuid.UUID,
    data: WhitelistEntryCreate,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    settings = await service.add_chat_to_whitelist(session, account_id, data.chat_id)
    return TelegramSettingsRead.model_validate(settings)


@router.delete("/{account_id}/whitelist/{chat_id}", response_model=TelegramSettingsRead)
async def remove_chat_from_whitelist(
    account_id: uuid.UUID,
    chat_id: int,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramSettingsService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    settings = await service.remove_chat_from_whitelist(session, account_id, chat_id)
    return TelegramSettingsRead.model_validate(settings)


router.include_router(
    create_crud_router(
        get_service=get_telegram_settings_service,
        create_schema=TelegramSettingsCreate,
        update_schema=TelegramSettingsUpdate,
        response_schema=TelegramSettingsRead,
        prefix="/settings",
        tags=["Telegram Settings"],
        entity_name="TelegramSettings",
    )
)
