"""Telegram account, chat and message endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.dependencies import get_telegram_account_service
from src.modules.telegram_clients.schemas.public import (
    AccountRead,
    ChatRead,
    MediaItem,
    MessageRead,
)
from src.modules.telegram_clients.services import TelegramAccountService

router = APIRouter()

ACCOUNT_FILTER_FIELDS = {
    "id", "telegram_id", "phone", "is_connected", "first_name",
    "last_name", "username", "created_at", "updated_at",
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
    accounts, total = await service.get_accounts(
        session,
        parsed,
        (page - 1) * limit,
        limit,
        order_by,
    )
    return PaginatedResponse.from_list(accounts, total, page=page, page_size=limit)


@router.get("/{account_id}", response_model=AccountRead, summary="Telegram-аккаунт")
async def get_account(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> AccountRead:
    account = await service.get_by_id(session, account_id)
    if not account:
        raise NotFoundError(detail="Telegram-аккаунт не найден")
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить Telegram-аккаунт")
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
    return await service.get_chats(session, account_id, limit=limit)


@router.get("/{account_id}/chats/{chat_id}/messages", response_model=list[MessageRead], summary="Сообщения чата")
async def get_messages(
    account_id: uuid.UUID,
    chat_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset_id: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramAccountService = Depends(get_telegram_account_service),
) -> list[MessageRead]:
    messages = await service.get_messages(session, account_id, chat_id, limit=limit, offset_id=offset_id)
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
