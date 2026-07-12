"""
Публичные роуты модуля Telegram-клиентов.

auth_id извлекается из JWT-токена.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_current_user, get_db_session
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.dependencies import (
    get_telegram_client_service,
    get_telegram_settings_service,
)
from src.modules.telegram_clients.schemas.internal.settings import (
    TelegramSettingsCreate,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
)
from src.modules.telegram_clients.schemas.public import (
    AccountRead,
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
from src.modules.telegram_clients.service import TelegramClientService

router = APIRouter(prefix="/api/v1/public/telegram")


@router.post(
    "/auth/phone",
    response_model=AuthStep1Response,
    summary="Шаг 1: отправить номер телефона",
)
async def auth_phone(
    data: PhoneRequest,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> AuthStep1Response:
    """Отправляет SMS-код на указанный номер телефона."""
    return await service.request_code(session, data.model_dump(), auth_id)


@router.post(
    "/auth/code",
    response_model=AuthStep2Response,
    summary="Шаг 2: ввести SMS-код",
)
async def auth_code(
    data: CodeRequest,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> AuthStep2Response:
    """Вводит SMS-код. Если аккаунт с 2FA — возвращает статус 2fa_required."""
    return await service.verify_code(session, data.model_dump(), auth_id)


@router.post(
    "/auth/password",
    response_model=AuthStep3Response,
    summary="Шаг 3: ввести пароль 2FA",
)
async def auth_password(
    data: PasswordRequest,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> AuthStep3Response:
    """Вводит пароль облачного шифрования (2FA)."""
    return await service.verify_password(session, data.model_dump(), auth_id)


# --- QR-авторизация ---


@router.post(
    "/auth/qr",
    response_model=QrStartResponse,
    summary="Запустить QR-авторизацию Telegram",
)
async def auth_qr_start(
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> QrStartResponse:
    """Создаёт QR-сессию для авторизации Telegram через сканирование QR-кода."""
    return await service.start_qr_auth(session, auth_id)


@router.get(
    "/auth/qr/{account_id}/status",
    response_model=QrStatusResponse,
    summary="Статус QR-авторизации",
)
async def auth_qr_status(
    account_id: uuid.UUID,
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> QrStatusResponse:
    """Возвращает текущий статус QR-сессии: pending, connected, expired или error."""
    return await service.get_qr_status(account_id)


@router.delete(
    "/auth/qr/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отменить QR-авторизацию",
)
async def auth_qr_cancel(
    account_id: uuid.UUID,
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> None:
    """Отменяет QR-сессию и очищает временные данные."""
    await service.cancel_qr_auth(account_id)


@router.post(
    "/auth/qr/{account_id}/complete",
    response_model=AccountRead,
    summary="Завершить QR-авторизацию",
)
async def auth_qr_complete(
    account_id: uuid.UUID,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> AccountRead:
    """Создаёт запись аккаунта в БД после успешного QR-сканирования."""
    return await service.complete_qr_auth(session, auth_id, account_id)


# --- Управление аккаунтами ---


@router.get(
    "/",
    response_model=PaginatedResponse[AccountRead],
    summary="Список Telegram-аккаунтов",
)
async def get_accounts(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> PaginatedResponse:
    """Возвращает все Telegram-аккаунты текущего пользователя с фильтрацией и пагинацией."""
    parsed = parse_filters(filters)
    skip = (page - 1) * limit
    accounts, total = await service.get_accounts(session, auth_id, parsed, skip, limit)
    return PaginatedResponse.from_list(accounts, total, page=page, page_size=limit)


@router.get(
    "/{account_id}",
    response_model=AccountRead,
    summary="Детальный просмотр Telegram-аккаунта",
)
async def get_account(
    account_id: uuid.UUID,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> AccountRead:
    """Получить детализацию Telegram-аккаунта по ID."""
    account = await service.get_by_id(session, account_id)
    if not account or account.auth_id != auth_id:
        raise NotFoundError(detail="Telegram-аккаунт не найден")
    return account


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить Telegram-аккаунт",
)
async def delete_account(
    account_id: uuid.UUID,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> None:
    """Удаляет Telegram-аккаунт, отключает клиент, удаляет сессию."""
    await service.delete_account(session, account_id, auth_id)


# --- Чаты и сообщения ---


@router.get(
    "/{account_id}/chats",
    response_model=list[ChatRead],
    summary="Список чатов аккаунта",
)
async def get_chats(
    account_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> list[ChatRead]:
    """Возвращает все чаты указанного Telegram-аккаунта."""
    return await service.get_chats(session, account_id, auth_id, limit=limit)


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
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_client_service),
) -> list[MessageRead]:
    """Возвращает сообщения указанного чата (on-demand из Telegram API)."""
    domain_messages = await service.get_messages(
        session, account_id, chat_id, auth_id, limit=limit, offset_id=offset_id
    )
    return [
        MessageRead(
            id=m.message_id,
            chat_id=m.chat_id,
            sender_id=m.sender_id,
            text=m.text,
            media=[
                MediaItem(id=str(media.telegram_id), type=media.type)
                for media in m.media
            ],
            date=m.date,
        )
        for m in domain_messages
    ]


# --- Настройки чтения ---


@router.get(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    summary="Настройки чтения аккаунта",
)
async def get_settings(
    account_id: uuid.UUID,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Получить настройки чтения для своего Telegram-аккаунта."""
    # Проверяем принадлежность аккаунта
    account = await service.repository.get_by_id(session, account_id)
    if not account or account.auth_id != auth_id:
        raise NotFoundError(detail="Telegram-аккаунт не найден")

    settings = await service.get_settings(session, account_id)
    return TelegramSettingsRead.model_validate(settings)


@router.post(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать настройки чтения аккаунта",
)
async def create_settings(
    account_id: uuid.UUID,
    data: TelegramSettingsCreate,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Создать настройки чтения для своего Telegram-аккаунта."""
    # Проверяем принадлежность аккаунта
    account = await service.repository.get_by_id(session, account_id)
    if not account or account.auth_id != auth_id:
        raise NotFoundError(detail="Telegram-аккаунт не найден")

    settings = await service._create_default_settings(session, account_id)
    # Если переданы кастомные значения - обновляем
    if data.model_dump(exclude_unset=True):
        settings = await service.update_settings(
            session, account_id, data.model_dump(exclude_unset=True)
        )
    return TelegramSettingsRead.model_validate(settings)


@router.put(
    "/{account_id}/settings",
    response_model=TelegramSettingsRead,
    summary="Обновить настройки чтения аккаунта",
)
async def update_settings(
    account_id: uuid.UUID,
    data: TelegramSettingsUpdate,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> TelegramSettingsRead:
    """Обновить настройки чтения для своего Telegram-аккаунта."""
    # Проверяем принадлежность аккаунта
    account = await service.repository.get_by_id(session, account_id)
    if not account or account.auth_id != auth_id:
        raise NotFoundError(detail="Telegram-аккаунт не найден")

    settings = await service.update_settings(
        session, account_id, data.model_dump(exclude_unset=True)
    )
    return TelegramSettingsRead.model_validate(settings)


@router.delete(
    "/{account_id}/settings",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить настройки чтения аккаунта",
)
async def delete_settings(
    account_id: uuid.UUID,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: TelegramClientService = Depends(get_telegram_settings_service),
) -> None:
    """Удалить настройки чтения для своего Telegram-аккаунта."""
    # Проверяем принадлежность аккаунта
    account = await service.repository.get_by_id(session, account_id)
    if not account or account.auth_id != auth_id:
        raise NotFoundError(detail="Telegram-аккаунт не найден")

    await service.delete_settings(session, account_id)
