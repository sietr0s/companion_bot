"""
Менеджер Telegram-клиентов (singleton).

Управляет жизненным циклом Telethon-клиентов:
- Подключение и отключение аккаунтов
- Обработка входящих сообщений → делегирует в сервис
- Отправка сообщений через Telethon
"""
import logging
import os
import uuid
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from src.core.config import settings
from src.core.database import async_session_factory
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.schemas.events import Media, TgMessageReceived

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """
    Singleton-менеджер Telethon-клиентов.

    Держит все активные подключения в памяти.
    При старте приложения загружает все сессии из БД.
    """

    def __init__(self) -> None:
        self._clients: dict[uuid.UUID, TelegramClient] = {}
        self._phone_code_hashes: dict[uuid.UUID, str] = {}
        self._service = None

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

    def set_service(self, service: Any) -> None:
        """
        Установить сервис для обработки входящих сообщений.

        Вызывается после создания сервиса для регистрации обратного вызова.
        """
        self._service = service

    def _register_message_handler(self, account_id: uuid.UUID, client: TelegramClient) -> None:
        """Регистрирует обработчик входящих сообщений для клиента."""

        @client.on(events.NewMessage)
        async def on_new_message(event: events.NewMessage.Event) -> None:
            """
            Обработать входящее сообщение.

            Делегирует обработку в сервис.
            """
            if self._service is None:
                logger.error("Сервис не установлен для обработки сообщений")
                return

            async with async_session_factory() as session:
                await self._service.handle_incoming_message(
                    session=session,
                    client=client,
                    account_id=account_id,
                    event=event,
                )

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
            Список Media объектов
        """
        media: list[Media] = []

        if not message.media:
            return media

        media_type = type(message.media).__name__.lower()
        telegram_file_id = message.media.id

        media.append(Media(
            telegram_id=telegram_file_id,
            type=media_type,
        ))

        return media

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
        last_read_message_id: int | None = None,
    ) -> list[TgMessageReceived]:
        """
        Получить непрочитанные сообщения чата.

        Args:
            account_id: ID аккаунта
            chat_id: ID чата в Telegram
            last_read_message_id: ID последнего прочитанного сообщения

        Returns:
            Список событий TgMessageReceived с message_id > last_read_message_id
        """
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не подключён" % account_id)

        messages: list[TgMessageReceived] = []
        async for msg in client.iter_messages(chat_id, offset_id=last_read_message_id):
            if last_read_message_id and msg.id <= last_read_message_id:
                break

            media = await self.extract_media(client, msg)
            messages.append(
                TgMessageReceived(
                    account_id=account_id,
                    chat_id=chat_id,
                    message_id=msg.id,
                    sender_id=msg.sender_id,
                    text=msg.text or "",
                    media=media,
                )
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

    async def stop_all(self) -> None:
        """Отключить все клиенты при остановке приложения."""
        for account_id in list(self._clients.keys()):
            await self.disconnect_account(account_id)
