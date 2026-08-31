"""Telegram phone and QR authentication endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.modules.telegram_clients.dependencies import get_telegram_account_service
from src.modules.telegram_clients.schemas.public import (
    AccountRead,
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
    CodeRequest,
    PasswordRequest,
    PhoneRequest,
    QrStartResponse,
    QrStatusResponse,
)
from src.modules.telegram_clients.services import TelegramAccountService

router = APIRouter(prefix="/auth")


@router.post("/phone", response_model=AuthStep1Response, summary="Шаг 1: отправить номер телефона")
async def auth_phone(
    data: PhoneRequest,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AuthStep1Response:
    return await service.request_code(session, data.model_dump())


@router.post("/code", response_model=AuthStep2Response, summary="Шаг 2: ввести SMS-код")
async def auth_code(
    data: CodeRequest,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AuthStep2Response:
    return await service.verify_code(session, data.model_dump())


@router.post("/password", response_model=AuthStep3Response, summary="Шаг 3: ввести пароль 2FA")
async def auth_password(
    data: PasswordRequest,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AuthStep3Response:
    return await service.verify_password(session, data.model_dump())


@router.post("/qr", response_model=QrStartResponse, summary="Запустить QR-авторизацию Telegram")
async def auth_qr_start(
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> QrStartResponse:
    return await service.start_qr_auth(session)


@router.get("/qr/{account_id}/status", response_model=QrStatusResponse, summary="Статус QR-авторизации")
async def auth_qr_status(
    account_id: uuid.UUID,
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> QrStatusResponse:
    return await service.get_qr_status(account_id)


@router.delete("/qr/{account_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Отменить QR-авторизацию")
async def auth_qr_cancel(
    account_id: uuid.UUID,
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> None:
    await service.cancel_qr_auth(account_id)


@router.post("/qr/{account_id}/complete", response_model=AccountRead, summary="Завершить QR-авторизацию")
async def auth_qr_complete(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AccountRead:
    return await service.complete_qr_auth(session, account_id)
