"""Manager routes grouped by entity; authentication is applied by the level router."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.routers import create_crud_router
from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.modules.instagram_clients.dependencies import (
    get_instagram_settings_repository,
    get_instagram_settings_service,
)
from src.modules.instagram_clients.repository import InstagramSettingsRepository
from src.modules.instagram_clients.schemas.api import (
    InstagramSettingsCreate,
    InstagramSettingsRead,
    InstagramSettingsUpdate,
    InstagramWhitelistEntryCreate,
)
from src.modules.instagram_clients.services import InstagramSettingsService

router = APIRouter()


@router.get("/{account_id}/settings", response_model=InstagramSettingsRead)
async def get_settings(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    repository: InstagramSettingsRepository = Depends(get_instagram_settings_repository),
) -> InstagramSettingsRead:
    settings = await repository.get_by_account_id(session, account_id)
    if not settings:
        raise NotFoundError(detail="Настройки не найдены")
    return InstagramSettingsRead.model_validate(settings)


@router.post(
    "/{account_id}/settings",
    response_model=InstagramSettingsRead,
    status_code=status.HTTP_201_CREATED,
)
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


@router.put("/{account_id}/settings", response_model=InstagramSettingsRead)
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


router.include_router(
    create_crud_router(
        get_service=get_instagram_settings_service,
        create_schema=InstagramSettingsCreate,
        update_schema=InstagramSettingsUpdate,
        response_schema=InstagramSettingsRead,
        prefix="/settings",
        tags=["Instagram Settings"],
        entity_name="InstagramSettings",
    )
)
