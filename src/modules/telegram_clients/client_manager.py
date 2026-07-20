"""
Менеджер Telegram-клиентов (singleton) — единый класс.

Содержит всю логику работы с Telethon:
- Реестр активных клиентов
- Авторизация (SMS-код, пароль, QR)
- Сообщения и чаты
- Управление сессиями
- Обработка входящих сообщений
"""

import logging
import os
import uuid
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from src.core.config import settings
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.domain import Media, Message, Sender
from src.modules.telegram_clients.qr_auth import QrAuthManager

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """
    Единый менеджер Telegram-клиентов.

    Хранит:
    - _clients: реестр подключённых TelegramClient
    - _service: сервис для обработки входящих сообщений
    - _phone_code_hashes, _phones: данные SMS-авторизации
    - _qr_auth: отдельный координатор QR-сессий
    """

    def __init__(self) -> None:
        self._clients: dict[uuid.UUID, TelegramClient] = {}
        self._phone_code_hashes: dict[uuid.UUID, str] = {}
        self._phones: dict[uuid.UUID, str] = {}
        self._service = None
        self._qr_auth = QrAuthManager(
            create_client=self.create_client,
            get_session_path=self.get_session_path,
            get_client=self.get_client,
            set_client=self.set_client,
            remove_client=self.remove_client,
        )

    # ── Управление клиентами ────────────────────────────────────────

    def get_client(self, account_id: uuid.UUID) -> TelegramClient | None:
        """Получить клиент по ID аккаунта."""
        return self._clients.get(account_id)

    def set_client(self, account_id: uuid.UUID, client: TelegramClient) -> None:
        """Сохранить клиент в реестре."""
        self._clients[account_id] = client

    def remove_client(self, account_id: uuid.UUID) -> TelegramClient | None:
        """Удалить клиент из реестра и вернуть его."""
        return self._clients.pop(account_id, None)

    def get_all_client_ids(self) -> list[uuid.UUID]:
        """Получить список всех ID клиентов."""
        return list(self._clients.keys())

    def get_service(self) -> Any:
        """Получить сервис для обработки входящих сообщений."""
        return self._service

    def set_service(self, service: Any) -> None:
        """Установить сервис для обработки входящих сообщений."""
        self._service = service

    def get_session_path(self, account_id: uuid.UUID) -> str:
        """Формирует путь к session-файлу."""
        session_dir = settings.TG_SESSION_DIR
        os.makedirs(session_dir, exist_ok=True)
        return os.path.join(session_dir, str(account_id))

    def create_client(self, session_path: str) -> TelegramClient:
        """Создаёт экземпляр TelegramClient."""
        return TelegramClient(
            session_path,
            settings.TG_API_ID,
            settings.TG_API_HASH,
            app_version=settings.TG_APP_VERSION,
            system_version=settings.TG_SYSTEM_VERSION,
            device_model=settings.TG_DEVICE_MODEL,
        )

    # ── Авторизация (SMS-код) ──────────────────────────────────────

    async def send_code(self, phone: str, account_id: uuid.UUID) -> str:
        """
        Отправить SMS-код на номер телефона.

        Создаёт временный клиент, отправляет код и возвращает
        phone_code_hash для последующей верификации.
        """
        session_path = self.get_session_path(account_id)
        logger.info(
            "[tg client] send_code: account_id=%s, phone=%s, session_path=%s",
            account_id,
            phone,
            session_path,
        )
        client = self.create_client(session_path)
        await client.connect()
        logger.info(
            "[tg client] connected: account_id=%s, authorized=%s",
            account_id,
            await client.is_user_authorized(),
        )

        result = await client.send_code_request(phone)
        self._phone_code_hashes[account_id] = result.phone_code_hash

        # Логируем тип доставки кода
        code_type = getattr(result, "type", None)
        timeout = getattr(result, "timeout", None)
        next_type = getattr(result, "next_type", None)
        logger.info(
            "[tg client] send_code done: account_id=%s, phone_code_hash=%s, "
            "code_type=%s, timeout=%s, next_type=%s",
            account_id,
            result.phone_code_hash,
            code_type,
            timeout,
            next_type,
        )

        # Сохраняем номер для последующего sign_in
        self._phones[account_id] = phone

        # Клиент будет переиспользован при sign_in
        self.set_client(account_id, client)
        return result.phone_code_hash

    async def sign_in_with_code(self, account_id: uuid.UUID, code: str) -> str:
        """
        Войти по SMS-коду.

        Возвращает "connected", "2fa_required" или "invalid_code".
        """
        client = self.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не найден")

        phone_code_hash = self._phone_code_hashes.get(account_id, "")
        phone = self._phones.get(account_id, "")
        logger.info(
            "[tg client] sign_in: account_id=%s, phone=%s, code=%s, phone_code_hash=%s",
            account_id,
            phone,
            code,
            phone_code_hash,
        )

        try:
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=phone_code_hash,
            )
            logger.info("[tg client] sign_in connected: account_id=%s", account_id)
            return "connected"
        except SessionPasswordNeededError:
            logger.info("[tg client] sign_in 2fa required: account_id=%s", account_id)
            return "2fa_required"
        except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
            logger.warning(
                "[tg client] sign_in invalid/expired code: account_id=%s, %s",
                account_id,
                e,
            )
            return "invalid_code"
        except Exception as e:
            logger.exception("[tg client] sign_in error: account_id=%s, %s", account_id, e)
            raise

    async def sign_in_with_password(self, account_id: uuid.UUID, password: str) -> str:
        """Войти по паролю облачного шифрования (2FA)."""
        client = self.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не найден")

        await client.sign_in(password=password)
        return "connected"

    # ── QR-авторизация ─────────────────────────────────────────────

    async def start_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """
        Запустить QR-авторизацию.

        Создаёт временный клиент, запускает qr_login() и фоновый worker.
        """
        return await self._qr_auth.start(account_id)

    def get_qr_status(self, account_id: uuid.UUID) -> dict[str, str]:
        """Получить статус QR-сессии."""
        return self._qr_auth.status(account_id)

    async def cancel_qr_login(self, account_id: uuid.UUID) -> None:
        """Отменить QR-авторизацию."""
        await self._qr_auth.cancel(account_id)

    async def complete_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """
        Завершить QR-авторизацию: получить данные пользователя из Telegram.
        """
        return await self._qr_auth.complete(account_id)

    # ── Сообщения и медиа ──────────────────────────────────────────

    async def extract_media(
        self,
        client: TelegramClient,
        message: Any,
    ) -> list[Media]:
        """Извлечь медиа из сообщения Telegram."""
        media: list[Media] = []

        if not message.media:
            return media

        media_type = type(message.media).__name__.lower()

        telegram_file_id = None
        if hasattr(message.media, "photo") and message.media.photo:
            telegram_file_id = message.media.photo.id
        elif hasattr(message.media, "document") and message.media.document:
            telegram_file_id = message.media.document.id

        if telegram_file_id is None:
            return media

        media.append(
            Media(
                telegram_id=telegram_file_id,
                type=media_type,
            )
        )

        return media

    async def send_message(self, account_id: uuid.UUID, chat_id: int, text: str) -> None:
        """Отправить сообщение через указанный аккаунт."""
        client = self.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не подключён")
        await client.send_message(chat_id, text)

    async def get_chats(self, account_id: uuid.UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Получить список чатов аккаунта из Telegram API."""
        client = self.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не подключён")

        chats = []
        async for dialog in client.iter_dialogs(limit=limit):
            chats.append(
                {
                    "id": dialog.id,
                    "name": dialog.name,
                    "chat_type": dialog.entity.__class__.__name__.lower()
                    if dialog.entity
                    else "unknown",
                    "username": dialog.entity.username
                    if hasattr(dialog.entity, "username")
                    else None,
                }
            )
        return chats

    async def get_messages(
        self,
        account_id: uuid.UUID,
        chat_id: int,
        last_read_message_id: int | None = None,
        limit: int = 50,
        offset_id: int = 0,
    ) -> list[Message]:
        """
        Получить непрочитанные сообщения чата.
        """
        client = self.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не подключён")

        effective_offset = last_read_message_id or offset_id

        messages: list[Message] = []
        async for msg in client.iter_messages(chat_id, limit=limit, offset_id=effective_offset):
            if last_read_message_id and msg.id <= last_read_message_id:
                break

            media = await self.extract_media(client, msg)
            telegram_sender = await msg.get_sender()
            messages.append(
                Message(
                    account_id=account_id,
                    chat_id=chat_id,
                    message_id=msg.id,
                    sender=Sender(
                        sender_id=msg.sender_id,
                        username=getattr(telegram_sender, "username", None),
                        first_name=getattr(telegram_sender, "first_name", None),
                        last_name=getattr(telegram_sender, "last_name", None),
                    ),
                    text=msg.text or "",
                    media=media,
                    date=msg.date,
                )
            )
        return messages

    async def get_me(self, account_id: uuid.UUID) -> dict[str, Any] | None:
        """Получить информацию о текущем пользователе Telegram."""
        client = self.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не подключён")
        me = await client.get_me()
        if not me:
            return None
        return {
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "telegram_id": me.id,
        }

    # ── Управление сессиями ────────────────────────────────────────

    async def connect_account(self, account_id: uuid.UUID) -> bool:
        """
        Подключить аккаунт по существующей сессии.

        Используется при старте приложения для восстановления подключений.
        """
        session_path = self.get_session_path(account_id)
        client = self.create_client(session_path)
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            logger.warning("Сессия аккаунта %s не авторизована", account_id)
            return False

        self.set_client(account_id, client)
        logger.info("Аккаунт %s подключён", account_id)
        return True

    async def disconnect_account(self, account_id: uuid.UUID) -> None:
        """Отключить аккаунт и удалить клиент из памяти."""
        client = self.remove_client(account_id)
        if client:
            await client.disconnect()
            logger.info("Аккаунт %s отключён", account_id)

    async def stop_all(self) -> None:
        """Отключить все клиенты при остановке приложения."""
        await self._qr_auth.stop()
        for account_id in list(self.get_all_client_ids()):
            await self.disconnect_account(account_id)
