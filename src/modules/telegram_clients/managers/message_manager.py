"""
Менеджер сообщений и медиа Telegram-клиентов.

Отвечает за:
- Отправка сообщений
- Получение списка чатов
- Получение сообщений из чата
- Извлечение медиа из сообщений
- Получение информации о пользователе (get_me)
"""

import logging
import uuid
from typing import Any

from telethon import TelegramClient

from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.domain import Media, Message

logger = logging.getLogger(__name__)


class TelegramMessageManager:
    """
    Менеджер сообщений и медиа Telegram-клиентов.

    Содержит логику отправки сообщений, получения чатов и сообщений,
    а также извлечения медиа-вложений.
    Для доступа к клиентам использует TelegramClientManager (фасад).
    """

    def __init__(self, client_manager: Any) -> None:
        """
        Args:
            client_manager: Ссылка на TelegramClientManager (фасад),
                            через который получает доступ к _clients.
        """
        self._client_manager = client_manager

    async def extract_media(
        self,
        client: TelegramClient,
        message: Any,
    ) -> list[Media]:
        """
        Извлечь медиа из сообщения Telegram.

        Args:
            client: Telegram клиент
            message: Сообщение Telegram

        Returns:
            Список доменных Media объектов
        """
        media: list[Media] = []

        if not message.media:
            return media

        media_type = type(message.media).__name__.lower()

        # Безопасно извлекаем ID: photo.id или document.id
        telegram_file_id = None
        if hasattr(message.media, "photo") and message.media.photo:
            telegram_file_id = message.media.photo.id
        elif hasattr(message.media, "document") and message.media.document:
            telegram_file_id = message.media.document.id

        if telegram_file_id is None:
            return media

        media.append(Media(
            telegram_id=telegram_file_id,
            type=media_type,
        ))

        return media

    async def send_message(self, account_id: uuid.UUID, chat_id: int, text: str) -> None:
        """Отправить сообщение через указанный аккаунт."""
        client = self._client_manager.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не подключён")
        await client.send_message(chat_id, text)

    async def get_chats(self, account_id: uuid.UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Получить список чатов аккаунта из Telegram API."""
        client = self._client_manager.get_client(account_id)
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

        Args:
            account_id: ID аккаунта
            chat_id: ID чата в Telegram
            last_read_message_id: ID последнего прочитанного сообщения
            limit: максимальное количество сообщений
            offset_id: ID сообщения для пагинации

        Returns:
            Список доменных Message
        """
        client = self._client_manager.get_client(account_id)
        if not client:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не подключён")

        effective_offset = last_read_message_id or offset_id

        messages: list[Message] = []
        async for msg in client.iter_messages(chat_id, limit=limit, offset_id=effective_offset):
            if last_read_message_id and msg.id <= last_read_message_id:
                break

            media = await self._client_manager.extract_media(client, msg)
            messages.append(
                Message(
                    account_id=account_id,
                    chat_id=chat_id,
                    message_id=msg.id,
                    sender_id=msg.sender_id,
                    text=msg.text or "",
                    media=media,
                    date=msg.date,
                )
            )
        return messages

    async def get_me(self, account_id: uuid.UUID) -> dict[str, Any] | None:
        """Получить информацию о текущем пользователе Telegram."""
        client = self._client_manager.get_client(account_id)
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
