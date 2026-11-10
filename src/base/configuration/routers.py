"""Generate each module's own manager configuration endpoints."""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.configuration.contracts import ConfigPatch, ConfigRead, ConfigReset
from src.base.configuration.service import BaseConfigService
from src.core.dependencies import get_current_admin, get_db_session
from src.core.routers import create_manager_router


def create_configuration_router(
    *, prefix: str, get_service: Callable[..., BaseConfigService[Any, Any]]
) -> APIRouter:
    router = create_manager_router(prefix=prefix, tags=["Configuration"])

    @router.get("", response_model=ConfigRead)
    async def read(
        session: AsyncSession = Depends(get_db_session),
        service: BaseConfigService[Any, Any] = Depends(get_service),
    ) -> ConfigRead:
        return await service.read(session)

    @router.patch("", response_model=ConfigRead)
    async def patch(
        data: ConfigPatch,
        actor: UUID = Depends(get_current_admin),
        session: AsyncSession = Depends(get_db_session),
        service: BaseConfigService[Any, Any] = Depends(get_service),
    ) -> ConfigRead:
        return await service.change(session, data.revision, data.values, actor)

    @router.post("/reset", response_model=ConfigRead)
    async def reset(
        data: ConfigReset,
        actor: UUID = Depends(get_current_admin),
        session: AsyncSession = Depends(get_db_session),
        service: BaseConfigService[Any, Any] = Depends(get_service),
    ) -> ConfigRead:
        return await service.change(
            session, data.revision, dict.fromkeys(data.fields), actor, reset=True
        )

    return router
