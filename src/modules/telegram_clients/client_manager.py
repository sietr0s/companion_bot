"""
Менеджер Telegram-клиентов (singleton) — фасад.

Делегирует вызовы специализированным менеджерам:
- TelegramAuthManager — авторизация (код, пароль, QR)
- TelegramMessageManager — чтение/отправка сообщений, медиа
- TelegramSessionManager — управление сессиями (подключение/отключение)

Сохраняет обратную совместимость: все публичные методы
TelegramClientManager доступны с теми же сигнатурами.
"""

import asyncio
import logging
import os
import uuid
from typing import Any

from telethon import TelegramClient

from src.core.config import settings
from src.modules.telegram_clients.managers.auth_manager import TelegramAuthManager
from src.modules.telegram_clients.managers.message_manager import TelegramMessageManager
from src.modules.telegram_clients.managers.session_manager import TelegramSessionManager
from src.modules.telegram_clients.domain import Media, Message

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """
    Singleton-менеджер Telethon-клиентов — фасад.

    Держит все активные подключения в памяти.
    При старте приложения загружает все сессии из БД.

    Делегирует вызовы:
    - self.auth_manager — авторизация
    - self.message_manager — сообщения и медиа
    - self.session_manager — сессии
    """

    def __init__(self) -> None:
        self._clients: dict[uuid.UUID, TelegramClient] = {}
        self._phone_code_hashes: dict[uuid.UUID, str] = {}
        self._qr_sessions: dict[uuid.UUID, dict[str, str]] = {}
        self._qr_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
        self._service = None

        # Инициализация специализированных менеджеров
        self.auth_manager = TelegramAuthManager(self)
        self.message_manager = TelegramMessageManager(self)
        self.session_manager = TelegramSessionManager(self)

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

    # ── Делегирование в TelegramAuthManager ─────────────────────────

    async def send_code(self, phone: str, account_id: uuid.UUID) -> str:
        """Делегирует в TelegramAuthManager.send_code."""
        return await self.auth_manager.send_code(phone, account_id)

    async def sign_in_with_code(self, account_id: uuid.UUID, code: str) -> str:
        """Делегирует в TelegramAuthManager.sign_in_with_code."""
        return await self.auth_manager.sign_in_with_code(account_id, code)

    async def sign_in_with_password(self, account_id: uuid.UUID, password: str) -> str:
        """Делегирует в TelegramAuthManager.sign_in_with_password."""
        return await self.auth_manager.sign_in_with_password(account_id, password)

    async def start_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Делегирует в TelegramAuthManager.start_qr_login."""
        return await self.auth_manager.start_qr_login(account_id)

    def get_qr_status(self, account_id: uuid.UUID) -> dict[str, str]:
        """Делегирует в TelegramAuthManager.get_qr_status."""
        return self.auth_manager.get_qr_status(account_id)

    async def cancel_qr_login(self, account_id: uuid.UUID) -> None:
        """Делегирует в TelegramAuthManager.cancel_qr_login."""
        await self.auth_manager.cancel_qr_login(account_id)

    async def complete_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Делегирует в TelegramAuthManager.complete_qr_login."""
        return await self.auth_manager.complete_qr_login(account_id)

    # ── Делегирование в TelegramMessageManager ──────────────────────

    async def extract_media(
        self,
        client: TelegramClient,
        message: Any,
    ) -> list[Media]:
        """Делегирует в TelegramMessageManager.extract_media."""
        return await self.message_manager.extract_media(client, message)

    async def send_message(self, account_id: uuid.UUID, chat_id: int, text: str) -> None:
        """Делегирует в TelegramMessageManager.send_message."""
        await self.message_manager.send_message(account_id, chat_id, text)

    async def get_chats(self, account_id: uuid.UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Делегирует в TelegramMessageManager.get_chats."""
        return await self.message_manager.get_chats(account_id, limit)

    async def get_messages(
        self,
        account_id: uuid.UUID,
        chat_id: int,
        last_read_message_id: int | None = None,
        limit: int = 50,
        offset_id: int = 0,
    ) -> list[Message]:
        """Делегирует в TelegramMessageManager.get_messages."""
        return await self.message_manager.get_messages(
            account_id, chat_id, last_read_message_id, limit, offset_id,
        )

    async def get_me(self, account_id: uuid.UUID) -> dict[str, Any] | None:
        """Делегирует в TelegramMessageManager.get_me."""
        return await self.message_manager.get_me(account_id)

    # ── Делегирование в TelegramSessionManager ──────────────────────

    async def connect_account(self, account_id: uuid.UUID) -> None:
        """Делегирует в TelegramSessionManager.connect_account."""
        await self.session_manager.connect_account(account_id)

    async def disconnect_account(self, account_id: uuid.UUID) -> None:
        """Делегирует в TelegramSessionManager.disconnect_account."""
        await self.session_manager.disconnect_account(account_id)

    async def stop_all(self) -> None:
        """Делегирует в TelegramSessionManager.stop_all."""
        await self.session_manager.stop_all()

    def set_service(self, service: Any) -> None:
        """Делегирует в TelegramSessionManager.set_service."""
        self.session_manager.set_service(service)

    def register_message_handler(self, account_id: uuid.UUID, client: TelegramClient) -> None:
        """Делегирует в TelegramSessionManager.register_message_handler."""
        self.session_manager.register_message_handler(account_id, client)
