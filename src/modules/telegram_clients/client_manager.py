"""
Менеджер Telegram-клиентов (singleton).

Управляет жизненным циклом Telethon-клиентов:
- Подключение и отключение аккаунтов
- Обработка входящих сообщений → публикация в шину
- Отправка сообщений через Telethon
"""

import logging
import os
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics
from src.core.clients.media_client import MediaClient
from src.core.config import settings
from src.core.database import async_session_factory
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.constants import ChatType
from src.modules.telegram_clients.repository import (
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.schemas.events import (
    TgMessageReceived,
)

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """
    Singleton-менеджер Telethon-клиентов.

    Держит все активные подключения в памяти.
    При старте приложения загружает все сессии из БД.
    """

    def __init__(self, message_bus: MessageBus) -> None:
        self._clients: dict[uuid.UUID, TelegramClient] = {}
        self._message_bus = message_bus
        self._phone_code_hashes: dict[uuid.UUID, str] = {}

    def _get_session_path(self, account_id: uuid.UUID) -> str:
        """Формирует путь к session-файлу."""
        session_dir = settings.TG_SESSION_DIR
        os.makedirs(session_dir, exist_ok=True)
        return os.path.join(session_dir, str(account_id))

    def _create_client(self, session_path: str) -> TelegramClient:
        """Создаёт экземпляр TelegramClient."""
        return TelegramClient(
            session_path,
            settings.TG_API_ID,
            settings.TG_API_HASH,
        )

    async def send_code(self, phone: str, account_id: uuid.UUID) -> str:
        """
        Отправить SMS-код на номер телефона.

        Создаёт временный клиент, отправляет код и возвращает
        phone_code_hash для последующей верификации.
        """
        session_path = self._get_session_path(account_id)
        client = self._create_client(session_path)
        await client.connect()

        result = await client.send_code_request(phone)
        self._phone_code_hashes[account_id] = result.phone_code_hash

        # Клиент будет переиспользован при sign_in
        self._clients[account_id] = client
        return result.phone_code_hash

    async def sign_in_with_code(self, account_id: uuid.UUID, code: str) -> str:
        """
        Войти по SMS-коду.

        Возвращает "connected" или "2fa_required".
        """
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не найден" % account_id)

        phone_code_hash = self._phone_code_hashes.get(account_id, "")

        try:
            await client.sign_in(
                phone=client.phone or "",
                code=code,
                phone_code_hash=phone_code_hash,
            )
            # Авторизация успешна — регистрируем обработчик входящих
            self._register_message_handler(account_id, client)
            return "connected"
        except SessionPasswordNeededError:
            return "2fa_required"

    async def sign_in_with_password(self, account_id: uuid.UUID, password: str) -> str:
        """Войти по паролю облачного шифрования (2FA)."""
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не найден" % account_id)

        await client.sign_in(password=password)
        self._register_message_handler(account_id, client)
        return "connected"

    async def connect_account(self, account_id: uuid.UUID) -> None:
        """
        Подключить аккаунт по существующей сессии.

        Используется при старте приложения для восстановления подключений.
        """
        session_path = self._get_session_path(account_id)
        client = self._create_client(session_path)
        await client.connect()

        # Проверяем, авторизован ли клиент
        if not await client.is_user_authorized():
            await client.disconnect()
            logger.warning("Сессия аккаунта %s не авторизована", account_id)
            return

        self._clients[account_id] = client
        self._register_message_handler(account_id, client)
        logger.info("Аккаунт %s подключён", account_id)

    async def disconnect_account(self, account_id: uuid.UUID) -> None:
        """Отключить аккаунт и удалить клиент из памяти."""
        client = self._clients.pop(account_id, None)
        if client:
            await client.disconnect()
            logger.info("Аккаунт %s отключён", account_id)

    def _register_message_handler(self, account_id: uuid.UUID, client: TelegramClient) -> None:
        """Регистрирует обработчик входящих сообщений для клиента."""

        @client.on(events.NewMessage)
        async def on_new_message(event: events.NewMessage.Event) -> None:
            """
            Обработать входящее сообщение.
            
            Выполняет:
            1. Проверка настроек (should_read_message)
            2. Публикация события в шину
            3. Обновление состояния чтения чата
            4. Загрузка медиа в storage
            """
            async with async_session_factory() as session:
                try:
                    # Определяем тип чата
                    if event.is_private:
                        chat_type = ChatType.PRIVATE
                    elif event.is_group:
                        chat_type = ChatType.GROUP
                    elif event.is_channel:
                        chat_type = ChatType.SUPERGROUP
                    else:
                        chat_type = ChatType.PRIVATE

                    should_read = await self.should_read_message(
                        session,
                        account_id,
                        event.chat_id,
                        chat_type,
                    )

                    if not should_read:
                        return  # Пропускаем сообщение согласно настройкам

                    # Извлекаем медиа из сообщения
                    media = await self._extract_media(client, event.message)

                    # Публикуем событие в шину
                    msg_event = TgMessageReceived(
                        account_id=account_id,
                        chat_id=event.chat_id,
                        message_id=event.message.id,
                        sender_id=event.sender_id,
                        text=event.message.text,
                        media=media,
                    )
                    await self._message_bus.publish(
                        BusTopics.TG_MESSAGE_RECEIVED, msg_event.to_bus_dict()
                    )

                    # Обновляем состояние чтения чата
                    chat_state_repo = TelegramChatStateRepository()
                    await chat_state_repo.upsert_last_read(
                        session=session,
                        account_id=account_id,
                        chat_id=event.chat_id,
                        message_id=event.message.id,
                    )
                    logger.info(
                        "Состояние чтения обновлено: account=%s, chat=%s, message_id=%s",
                        account_id,
                        event.chat_id,
                        event.message.id,
                    )

                    # Загружаем медиа в storage
                    if media:
                        await self._upload_media_to_storage(media)

                except asyncio.CancelledError:
                    logger.warning("Обработка входящего сообщения отменена для аккаунта %s", account_id)
                except (ConnectionError, TimeoutError) as e:
                    logger.error("Ошибка подключения при обработке сообщения для аккаунта %s: %s", account_id, e)
                except Exception as e:
                    logger.exception(
                        "Неожиданная ошибка при обработке входящего сообщения для аккаунта %s: %s",
                        account_id,
                        e,
                    )

    async def _extract_media(
        self,
        client: TelegramClient,
        message: Any,
    ) -> list[dict[str, str | None]]:
        """
        Извлечь медиа из сообщения Telegram.

        Args:
            client: Telegram клиент для скачивания медиа
            message: Сообщение Telegram

        Returns:
            Список словарей с информацией о медиа
        """
        media: list[dict[str, str | None]] = []

        if not message.media:
            return media

        media_type = type(message.media).__name__.lower()
        telegram_file_id = str(message.media.id) if hasattr(message.media, "id") else ""

        # Скачиваем медиа из Telegram
        media_bytes = await client.download_media(
            message.media,
            bytes=True,
        )

        # Определяем filename и content_type
        filename = f"{telegram_file_id}.dat"
        content_type = "application/octet-stream"

        media.append(
            {
                "type": media_type,
                "id": telegram_file_id,
                "data": media_bytes,
                "filename": filename,
                "content_type": content_type,
            }
        )

        return media

    async def _upload_media_to_storage(self, media: list[dict[str, str | None]]) -> None:
        """
        Загрузить медиа из Telegram в storage.

        Args:
            media: Список словарей с медиа (с temp_data)
        """
        media_client = MediaClient()

        for media_item in media:
            data = media_item.get("data")
            if data is None:
                continue

            filename = media_item.get("filename", "unknown.dat")
            content_type = media_item.get("content_type", "application/octet-stream")
            media_type = media_item.get("type", "unknown")
            telegram_id = media_item.get("id", "")

            storage_file_id = await media_client.upload_media_to_storage(
                file_bytes=data,
                filename=filename,
                content_type=content_type,
                is_public=False,
            )

            if storage_file_id:
                media_item["file_id"] = storage_file_id
                logger.info(
                    "Медиа загружено: type=%s, telegram_id=%s, storage_id=%s",
                    media_type,
                    telegram_id,
                    storage_file_id,
                )
            else:
                logger.warning("Не удалось загрузить медиа: %s", filename)

            # Удаляем data после загрузки если есть
            media_item.pop("data", None)

    async def send_message(self, account_id: uuid.UUID, chat_id: int, text: str) -> None:
        """Отправить сообщение через указанный аккаунт."""
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не подключён" % account_id)
        await client.send_message(chat_id, text)

    async def get_chats(self, account_id: uuid.UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Получить список чатов аккаунта из Telegram API."""
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не подключён" % account_id)

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
        limit: int = 50,
        offset_id: int = 0,
    ) -> list[dict[str, Any]]:
        """Получить сообщения чата из Telegram API (on-demand)."""
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не подключён" % account_id)

        messages = []
        async for msg in client.iter_messages(chat_id, limit=limit, offset_id=offset_id or None):
            # Извлекаем media
            media: list[dict[str, str]] = []
            if msg.media:
                media_type = type(msg.media).__name__.lower()
                media.append(
                    {
                        "type": media_type,
                        "id": str(msg.media.id) if hasattr(msg.media, "id") else "",
                    }
                )

            messages.append(
                {
                    "id": msg.id,
                    "chat_id": chat_id,
                    "sender_id": msg.sender_id,
                    "text": msg.text,
                    "media": media,
                    "date": msg.date.isoformat() if msg.date else None,
                }
            )
        return messages

    async def get_me(self, account_id: uuid.UUID) -> dict[str, Any] | None:
        """Получить информацию о текущем пользователе Telegram."""
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не подключён" % account_id)
        me = await client.get_me()
        if not me:
            return None
        return {
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "telegram_id": me.id,
        }

    async def should_read_message(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        chat_id: int,
        chat_type: ChatType,
    ) -> bool:
        """
        Проверить нужно ли читать сообщение из данного чата.

        Использует настройки TelegramSettings для аккаунта.
        Если whitelist_chat_ids задан - проверяет наличие chat_id в списке.
        Если whitelist пустой - читает все чаты разрешённых типов.

        Args:
            session: SQLAlchemy async сессия
            account_id: ID аккаунта
            chat_id: ID чата в Telegram
            chat_type: Тип чата (private, group, channel, etc.)

        Returns:
            True если сообщение нужно читать, False иначе
        """
        settings_repo = TelegramSettingsRepository()
        telegram_settings = await settings_repo.get_by_account_id(session, account_id)

        # Если настроек нет - читаем всё по умолчанию
        if not telegram_settings:
            return True

        # Проверка типа чата
        if chat_type == ChatType.PRIVATE and not telegram_settings.read_personal:
            return False
        if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP] and not telegram_settings.read_groups:
            return False
        if chat_type == ChatType.CHANNEL and not telegram_settings.read_channels:
            return False

        # Проверка whitelist
        if telegram_settings.whitelist_chat_ids:
            # Если whitelist задан - проверяем наличие chat_id
            return (
                str(chat_id) in telegram_settings.whitelist_chat_ids
                or chat_id in telegram_settings.whitelist_chat_ids
            )

        return True  # Если whitelist пустой - читать все чаты разрешённого типа

    async def stop_all(self) -> None:
        """Отключить все клиенты при остановке приложения."""
        for account_id in list(self._clients.keys()):
            await self.disconnect_account(account_id)
