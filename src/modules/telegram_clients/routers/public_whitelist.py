import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.modules.telegram_clients.dependencies import get_telegram_settings_service
from src.modules.telegram_clients.schemas.public import (
    TelegramSettingsRead,
    WhitelistEntryCreate,
)
from src.modules.telegram_clients.services import TelegramSettingsService

router = APIRouter()


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
