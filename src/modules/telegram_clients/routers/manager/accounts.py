"""Manager routes grouped by entity; authentication is applied by the level router."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.routers import create_crud_router
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.dependencies import (
    get_telegram_account_service,
)
from src.modules.telegram_clients.schemas.api import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
    ChatRead,
    CodeRequest,
    MediaItem,
    MessageRead,
    PasswordRequest,
    PhoneRequest,
    QrStartResponse,
    QrStatusResponse,
)
from src.modules.telegram_clients.services import TelegramAccountService

router = APIRouter()

ACCOUNT_FILTER_FIELDS = {
    "id",
    "telegram_id",
    "phone",
    "is_connected",
    "first_name",
    "last_name",
    "username",
    "created_at",
    "updated_at",
}


@router.get("/", response_model=PaginatedResponse[AccountRead], summary="Список Telegram-аккаунтов")
async def get_accounts(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> PaginatedResponse[AccountRead]:
    parsed = parse_filters(filters, allowed_fields=ACCOUNT_FILTER_FIELDS)
    accounts, total = await service.get_list(session, parsed, (page - 1) * limit, limit, order_by)
    return PaginatedResponse.from_list(
        [AccountRead.model_validate(account) for account in accounts],
        total,
        page=page,
        page_size=limit,
    )


@router.get("/{account_id}", response_model=AccountRead, summary="Telegram-аккаунт")
async def get_account(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AccountRead:
    account = await service.get_by_id(session, account_id)
    if not account:
        raise NotFoundError(detail="Telegram-аккаунт не найден")
    return AccountRead.model_validate(account)


@router.delete(
    "/{account_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить Telegram-аккаунт"
)
async def delete_account(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> None:
    await service.delete_account(session, account_id)


@router.get("/{account_id}/chats", response_model=list[ChatRead], summary="Список чатов аккаунта")
async def get_chats(
    account_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> list[ChatRead]:
    return [
        ChatRead.model_validate(chat)
        for chat in await service.get_chats(session, account_id, limit=limit)
    ]


@router.get(
    "/{account_id}/chats/{chat_id}/messages",
    response_model=list[MessageRead],
    summary="Сообщения чата",
)
async def get_messages(
    account_id: uuid.UUID,
    chat_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset_id: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> list[MessageRead]:
    messages = await service.get_messages(
        session, account_id, chat_id, limit=limit, offset_id=offset_id
    )
    return [
        MessageRead(
            id=message.message_id,
            chat_id=message.chat_id,
            sender_id=message.sender.sender_id,
            text=message.text,
            media=[MediaItem(id=str(item.telegram_id), type=item.type) for item in message.media],
            date=message.date,
        )
        for message in messages
    ]


@router.post(
    "/auth/phone", response_model=AuthStep1Response, summary="Шаг 1: отправить номер телефона"
)
async def auth_phone(
    data: PhoneRequest,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AuthStep1Response:
    return await service.request_code(session, data.model_dump())


@router.post("/auth/code", response_model=AuthStep2Response, summary="Шаг 2: ввести SMS-код")
async def auth_code(
    data: CodeRequest,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AuthStep2Response:
    return await service.verify_code(session, data.model_dump())


@router.post("/auth/password", response_model=AuthStep3Response, summary="Шаг 3: ввести пароль 2FA")
async def auth_password(
    data: PasswordRequest,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AuthStep3Response:
    return await service.verify_password(session, data.model_dump())


@router.post(
    "/auth/qr", response_model=QrStartResponse, summary="Запустить QR-авторизацию Telegram"
)
async def auth_qr_start(
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> QrStartResponse:
    return await service.start_qr_auth(session)


@router.get(
    "/auth/qr/{account_id}/status", response_model=QrStatusResponse, summary="Статус QR-авторизации"
)
async def auth_qr_status(
    account_id: uuid.UUID, service: TelegramAccountService = Depends(get_telegram_account_service)
) -> QrStatusResponse:
    return await service.get_qr_status(account_id)


@router.delete(
    "/auth/qr/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отменить QR-авторизацию",
)
async def auth_qr_cancel(
    account_id: uuid.UUID, service: TelegramAccountService = Depends(get_telegram_account_service)
) -> None:
    await service.cancel_qr_auth(account_id)


@router.post(
    "/auth/qr/{account_id}/complete", response_model=AccountRead, summary="Завершить QR-авторизацию"
)
async def auth_qr_complete(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AccountRead:
    return AccountRead.model_validate(await service.complete_qr_auth(session, account_id))


router.include_router(
    create_crud_router(
        get_service=get_telegram_account_service,
        create_schema=AccountCreate,
        update_schema=AccountUpdate,
        response_schema=AccountRead,
        prefix="/accounts",
        tags=["Telegram Accounts"],
        entity_name="TelegramAccount",
    )
)
