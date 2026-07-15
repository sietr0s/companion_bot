"""
Менеджер Telegram-клиентов (singleton) — фасад.

Единственный владелец состояния:
- Реестр активных Telethon-клиентов
- Сервис для обработки входящих сообщений
- Данные авторизации (phone_code_hashes, phones, QR-сессии)

Делегирует вызовы stateless-менеджерам, передавая self первым параметром.
"""

import logging
import os
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio

from telethon import TelegramClient

from src.core.config import settings
from src.modules.telegram_clients.domain import Media, Message
from src.modules.telegram_clients.managers import (
    auth_manager,
    message_manager,
    session_manager,
)

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """
    Фасад — владелец состояния Telegram-клиентов.

    Хранит:
    - _clients: реестр подключённых TelegramClient
    - _service: сервис для обработки входящих сообщений
    - _phone_code_hashes, _phones, _qr_sessions, _qr_tasks: данные авторизации
    """

    def __init__(self) -> None:
        self._clients: dict[uuid.UUID, TelegramClient] = {}
        self._phone_code_hashes: dict[uuid.UUID, str] = {}
        self._phones: dict[uuid.UUID, str] = {}
        self._qr_sessions: dict[uuid.UUID, dict[str, str]] = {}
        self._qr_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
        self._service = None

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
        logger.debug("TG_API_ID: %s", settings.TG_API_ID)
        logger.debug("TG_API_HASH: %s", settings.TG_API_HASH)
        return TelegramClient(
            session_path,
            settings.TG_API_ID,
            settings.TG_API_HASH,
            app_version=settings.TG_APP_VERSION,
            system_version=settings.TG_SYSTEM_VERSION,
            device_model=settings.TG_DEVICE_MODEL,
        )

    # ── Делегирование в stateless-менеджеры ─────────────────────────

    async def send_code(self, phone: str, account_id: uuid.UUID) -> str:
        """Делегирует в auth_manager.send_code."""
        return await auth_manager.send_code(self, phone, account_id)

    async def sign_in_with_code(self, account_id: uuid.UUID, code: str) -> str:
        """Делегирует в auth_manager.sign_in_with_code."""
        return await auth_manager.sign_in_with_code(self, account_id, code)

    async def sign_in_with_password(self, account_id: uuid.UUID, password: str) -> str:
        """Делегирует в auth_manager.sign_in_with_password."""
        return await auth_manager.sign_in_with_password(self, account_id, password)

    async def start_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Делегирует в auth_manager.start_qr_login."""
        return await auth_manager.start_qr_login(self, account_id)

    def get_qr_status(self, account_id: uuid.UUID) -> dict[str, str]:
        """Делегирует в auth_manager.get_qr_status."""
        return auth_manager.get_qr_status(self, account_id)

    async def cancel_qr_login(self, account_id: uuid.UUID) -> None:
        """Делегирует в auth_manager.cancel_qr_login."""
        await auth_manager.cancel_qr_login(self, account_id)

    async def complete_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Делегирует в auth_manager.complete_qr_login."""
        return await auth_manager.complete_qr_login(self, account_id)

    # ── Делегирование в message_manager ────────────────────────────

    async def extract_media(
        self,
        client: TelegramClient,
        message: Any,
    ) -> list[Media]:
        """Делегирует в message_manager.extract_media."""
        return await message_manager.extract_media(client, message)

    async def send_message(self, account_id: uuid.UUID, chat_id: int, text: str) -> None:
        """Делегирует в message_manager.send_message."""
        await message_manager.send_message(self, account_id, chat_id, text)

    async def get_chats(self, account_id: uuid.UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Делегирует в message_manager.get_chats."""
        return await message_manager.get_chats(self, account_id, limit)

    async def get_messages(
        self,
        account_id: uuid.UUID,
        chat_id: int,
        last_read_message_id: int | None = None,
        limit: int = 50,
        offset_id: int = 0,
    ) -> list[Message]:
        """Делегирует в message_manager.get_messages."""
        return await message_manager.get_messages(
            self, account_id, chat_id, last_read_message_id, limit, offset_id,
        )

    async def get_me(self, account_id: uuid.UUID) -> dict[str, Any] | None:
        """Делегирует в message_manager.get_me."""
        return await message_manager.get_me(self, account_id)

    # ── Делегирование в session_manager ────────────────────────────

    async def connect_account(self, account_id: uuid.UUID) -> None:
        """Делегирует в session_manager.connect_account."""
        await session_manager.connect_account(self, account_id)

    async def disconnect_account(self, account_id: uuid.UUID) -> None:
        """Делегирует в session_manager.disconnect_account."""
        await session_manager.disconnect_account(self, account_id)

    async def stop_all(self) -> None:
        """Делегирует в session_manager.stop_all."""
        await session_manager.stop_all(self)

    def register_message_handler(
        self, account_id: uuid.UUID, client: TelegramClient
    ) -> None:
        """Делегирует в session_manager.register_message_handler."""
        session_manager.register_message_handler(self, account_id, client)
