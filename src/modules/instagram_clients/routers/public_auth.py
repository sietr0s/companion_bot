import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.modules.instagram_clients.dependencies import get_instagram_account_service
from src.modules.instagram_clients.schemas.public import (
    InstagramAccountRead,
    InstagramCodeRequest,
    InstagramLoginRequest,
)
from src.modules.instagram_clients.services import InstagramAccountService

router = APIRouter()


@router.post("/accounts/{account_id}/login", response_model=InstagramAccountRead)
async def login(
    account_id: uuid.UUID,
    data: InstagramLoginRequest,
    session: AsyncSession = Depends(get_db_session),
    service: InstagramAccountService = Depends(get_instagram_account_service),
) -> InstagramAccountRead:
    account = await service.login(
        session, account_id, username=data.username, password=data.password
    )
    return InstagramAccountRead.model_validate(account)


@router.post("/accounts/{account_id}/two-factor", response_model=InstagramAccountRead)
async def two_factor(
    account_id: uuid.UUID,
    data: InstagramCodeRequest,
    session: AsyncSession = Depends(get_db_session),
    service: InstagramAccountService = Depends(get_instagram_account_service),
) -> InstagramAccountRead:
    account = await service.complete_two_factor(session, account_id, code=data.code)
    return InstagramAccountRead.model_validate(account)


@router.post("/accounts/{account_id}/challenge", response_model=InstagramAccountRead)
async def challenge(
    account_id: uuid.UUID,
    data: InstagramCodeRequest,
    session: AsyncSession = Depends(get_db_session),
    service: InstagramAccountService = Depends(get_instagram_account_service),
) -> InstagramAccountRead:
    account = await service.complete_challenge(session, account_id, code=data.code)
    return InstagramAccountRead.model_validate(account)
