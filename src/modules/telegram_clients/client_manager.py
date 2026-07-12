"""
Менеджер Telegram-клиентов (singleton).

Управляет жизненным циклом Telethon-клиентов:
- Подключение и отключение аккаунтов
- Обработка входящих сообщений → делегирует в сервис
- Отправка сообщений через Telethon
"""
import asyncio
import contextlib
import logging
import os
import uuid
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from src.core.config import settings
from src.core.database import async_session_factory
from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.constants import QrAuthStatus
from src.modules.telegram_clients.domain import Media, Message

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
        self._qr_sessions: dict[uuid.UUID, dict[str, str]] = {}
        self._qr_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
        self._service = None

    def _get_session_path(self, account_id: uuid.UUID) -> str:
        """Формирует путь к session-файлу."""
        session_dir = settings.TG_SESSION_DIR
        os.makedirs(session_dir, exist_ok=True)
        return os.path.join(session_dir, str(account_id))

    def _create_client(self, session_path: str) -> TelegramClient:
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

    async def send_code(self, phone: str, account_id: uuid.UUID) -> str:
        """
        Отправить SMS-код на номер телефона.

        Создаёт временный клиент, отправляет код и возвращает
        phone_code_hash для последующей верификации.
        """
        session_path = self._get_session_path(account_id)
        logger.info(
            "[tg client] send_code start: account_id=%s, phone=%s, session_path=%s",
            account_id,
            phone,
            session_path,
        )
        client = self._create_client(session_path)
        await client.connect()
        logger.info(
            "[tg client] connected to Telegram: account_id=%s, authorized=%s",
            account_id,
            await client.is_user_authorized(),
        )

        result = await client.send_code_request(phone)
        self._phone_code_hashes[account_id] = result.phone_code_hash

        # Логируем тип доставки кода (SMS / Telegram app / etc.)
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

        # Сохраняем номер для последующего sign_in, т.к. Telethon его не хранит
        client._phone = phone  # noqa: SLF001

        # Клиент будет переиспользован при sign_in
        self._clients[account_id] = client
        return result.phone_code_hash

    async def sign_in_with_code(self, account_id: uuid.UUID, code: str) -> str:
        """
        Войти по SMS-коду.

        Возвращает "connected", "2fa_required" или "invalid_code".
        """
        client = self._clients.get(account_id)
        if not client:
            logger.error("[tg client] sign_in: клиент не найден для account_id=%s", account_id)
            raise NotFoundError(detail="Клиент для account_id=%s не найден" % account_id)

        phone_code_hash = self._phone_code_hashes.get(account_id, "")
        phone = getattr(client, "_phone", "")
        logger.info(
            "[tg client] sign_in start: account_id=%s, phone=%s, code=%s, phone_code_hash=%s",
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
            # Авторизация успешна — регистрируем обработчик входящих
            self._register_message_handler(account_id, client)
            logger.info("[tg client] sign_in connected: account_id=%s", account_id)
            return "connected"
        except SessionPasswordNeededError:
            logger.info("[tg client] sign_in 2fa required: account_id=%s", account_id)
            return "2fa_required"
        except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
            logger.warning("[tg client] sign_in invalid/expired code: account_id=%s, %s", account_id, e)
            return "invalid_code"
        except Exception as e:
            logger.exception("[tg client] sign_in error: account_id=%s, %s", account_id, e)
            raise

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
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не подключён" % account_id)

        effective_offset = last_read_message_id or offset_id

        messages: list[Message] = []
        async for msg in client.iter_messages(chat_id, limit=limit, offset_id=effective_offset):
            if last_read_message_id and msg.id <= last_read_message_id:
                break

            media = await self.extract_media(client, msg)
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

    # ── QR-авторизация ─────────────────────────────────────────────

    async def _qr_wait_worker(self, account_id: uuid.UUID, client: TelegramClient, qr: Any) -> None:
        """Фоновый worker: ждёт сканирования QR-кода."""
        try:
            await qr.wait()
            self._qr_sessions[account_id] = {"status": QrAuthStatus.CONNECTED}
            self._register_message_handler(account_id, client)
            logger.info("[tg client] QR login connected: account_id=%s", account_id)
        except TimeoutError:
            self._qr_sessions[account_id] = {
                "status": QrAuthStatus.EXPIRED,
                "message": "QR-код истёк",
            }
            logger.warning("[tg client] QR login expired: account_id=%s", account_id)
        except Exception as e:
            self._qr_sessions[account_id] = {
                "status": QrAuthStatus.ERROR,
                "message": str(e),
            }
            logger.exception("[tg client] QR login error: account_id=%s, %s", account_id, e)

    async def start_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """
        Запустить QR-авторизацию.

        Создаёт временный клиент, запускает qr_login() и фоновый worker.
        Возвращает данные для QR-кода.
        """
        session_path = self._get_session_path(account_id)
        client = self._create_client(session_path)
        await client.connect()

        qr = await client.qr_login()
        expires_at: float | None = getattr(qr, "timeout", None)

        self._clients[account_id] = client
        self._qr_sessions[account_id] = {"status": QrAuthStatus.PENDING}

        task = asyncio.create_task(self._qr_wait_worker(account_id, client, qr))
        self._qr_tasks[account_id] = task

        logger.info(
            "[tg client] QR login started: account_id=%s, expires_at=%s",
            account_id,
            expires_at,
        )

        return {
            "qr_url": qr.url,
            "expires_at": expires_at,
        }

    def get_qr_status(self, account_id: uuid.UUID) -> dict[str, str]:
        """
        Получить статус QR-сессии.

        Возвращает {"status": ..., "message": ...}.
        """
        session = self._qr_sessions.get(account_id)
        if not session:
            return {"status": QrAuthStatus.ERROR, "message": "QR-сессия не найдена"}
        return dict(session)

    async def cancel_qr_login(self, account_id: uuid.UUID) -> None:
        """Отменить QR-авторизацию: остановить worker, отключить клиент, очистить данные."""
        task = self._qr_tasks.pop(account_id, None)
        if task and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        client = self._clients.pop(account_id, None)
        if client:
            await client.disconnect()

        self._qr_sessions.pop(account_id, None)
        logger.info("[tg client] QR login cancelled: account_id=%s", account_id)

    async def complete_qr_login(self, account_id: uuid.UUID) -> dict[str, Any]:
        """
        Завершить QR-авторизацию: получить данные пользователя из Telegram.

        Вызывается после того, как статус стал connected.
        """
        client = self._clients.get(account_id)
        if not client:
            raise NotFoundError(detail="Клиент для account_id=%s не найден" % account_id)

        me = await client.get_me()
        self._qr_sessions.pop(account_id, None)
        self._qr_tasks.pop(account_id, None)

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
