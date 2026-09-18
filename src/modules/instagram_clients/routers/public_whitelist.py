import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.modules.instagram_clients.dependencies import get_instagram_settings_service
from src.modules.instagram_clients.schemas.public import (
    InstagramSettingsRead,
    InstagramWhitelistEntryCreate,
)
from src.modules.instagram_clients.services import InstagramSettingsService

router = APIRouter()


@router.post("/{account_id}/whitelist", response_model=InstagramSettingsRead)
async def add_user_to_whitelist(
    account_id: uuid.UUID,
    data: InstagramWhitelistEntryCreate,
    session: AsyncSession = Depends(get_db_session),
    service: InstagramSettingsService = Depends(get_instagram_settings_service),
) -> InstagramSettingsRead:
    settings = await service.add_user_to_whitelist(session, account_id, data.user_pk)
    return InstagramSettingsRead.model_validate(settings)


@router.delete("/{account_id}/whitelist/{user_pk}", response_model=InstagramSettingsRead)
async def remove_user_from_whitelist(
    account_id: uuid.UUID,
    user_pk: int,
    session: AsyncSession = Depends(get_db_session),
    service: InstagramSettingsService = Depends(get_instagram_settings_service),
) -> InstagramSettingsRead:
    settings = await service.remove_user_from_whitelist(session, account_id, user_pk)
    return InstagramSettingsRead.model_validate(settings)
