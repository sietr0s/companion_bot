import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.modules.instagram_clients.dependencies import (
    get_instagram_settings_repository,
    get_instagram_settings_service,
)
from src.modules.instagram_clients.repository import InstagramSettingsRepository
from src.modules.instagram_clients.schemas.public import (
    InstagramSettingsCreate,
    InstagramSettingsRead,
    InstagramSettingsUpdate,
)
from src.modules.instagram_clients.services import InstagramSettingsService

router = APIRouter(prefix="/{account_id}/settings")


@router.get("", response_model=InstagramSettingsRead)
async def get_settings(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    repository: InstagramSettingsRepository = Depends(get_instagram_settings_repository),
) -> InstagramSettingsRead:
    settings = await repository.get_by_account_id(session, account_id)
    if not settings:
        raise NotFoundError(detail="Настройки не найдены")
    return InstagramSettingsRead.model_validate(settings)


@router.post("", response_model=InstagramSettingsRead, status_code=status.HTTP_201_CREATED)
async def create_settings(
    account_id: uuid.UUID,
    data: InstagramSettingsCreate,
    session: AsyncSession = Depends(get_db_session),
    service: InstagramSettingsService = Depends(get_instagram_settings_service),
) -> InstagramSettingsRead:
    settings = await service.create_default_settings(session, account_id)
    payload = data.model_dump(exclude_unset=True, exclude={"account_id"})
    if payload:
        settings = await service.update(session, settings.id, payload)
    return InstagramSettingsRead.model_validate(settings)


@router.put("", response_model=InstagramSettingsRead)
async def update_settings(
    account_id: uuid.UUID,
    data: InstagramSettingsUpdate,
    session: AsyncSession = Depends(get_db_session),
    service: InstagramSettingsService = Depends(get_instagram_settings_service),
    repository: InstagramSettingsRepository = Depends(get_instagram_settings_repository),
) -> InstagramSettingsRead:
    settings_obj = await repository.get_by_account_id(session, account_id)
    if not settings_obj:
        raise NotFoundError(detail="Настройки не найдены")
    settings = await service.update(session, settings_obj.id, data.model_dump(exclude_unset=True))
    return InstagramSettingsRead.model_validate(settings)
