"""
Сервис модуля Telegram-клиентов.

Содержит бизнес-логику авторизации, управления аккаунтами,
получения чатов и сообщений. Делегирует работу с Telethon
клиент-менеджеру, а персистентность — репозиторию.
"""

import asyncio
import logging
import os
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.events import NewMessage

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.telegram_clients.client_manager import TelegramClientManager
from src.modules.telegram_clients.constants import TgAuthStatus
from src.modules.telegram_clients.models import (
    TelegramAccount,
    TelegramChatState,
)
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.schemas.events import (
    Sender,
    TgAccountConnected,
    TgAccountDisconnected,
    TgMessageReceived,
)
from src.modules.telegram_clients.schemas.public import (
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
    QrStartResponse,
    QrStatusResponse,
)

logger = logging.getLogger(__name__)

class TelegramAccountService(
    BaseService[TelegramAccountRepository, TelegramAccount]
):
    """
    Сервис управления Telegram-аккаунтами.

    Координирует работу репозитория (БД) и клиент-менеджера (Telethon).
    """

    def __init__(
            self,
            repository: TelegramAccountRepository,
            message_bus: MessageProducer,
            client_manager: TelegramClientManager,
            settings_repository: TelegramSettingsRepository,
            chat_state_repository: TelegramChatStateRepository,
    ) -> None:
        super().__init__(repository)
        self.message_bus = message_bus
        self.client_manager = client_manager
        self.settings_repository = settings_repository
        self.chat_state_repository = chat_state_repository

    async def request_code(
            self, session: AsyncSession, data: dict
    ) -> AuthStep1Response:
        """
        Шаг 1 авторизации: отправить SMS-код на номер.

        Создаёт запись в БД и инициирует отправку кода через Telethon.
        """
        phone = data["phone"]
        account_id = uuid.uuid4()
        session_path = self.client_manager.get_session_path(account_id)

        logger.info(
            "[tg auth] Запрос кода: account_id=%s, phone=%s",
            account_id,
            phone,
        )

        await self.repository.create(
            session,
            {
                "id": account_id,
                "phone": phone,
                "session_file": session_path,
                "is_connected": False,
            },
        )

        # Отправляем код через Telethon
        phone_code_hash = await self.client_manager.send_code(phone, account_id)

        logger.info(
            "[tg auth] Код отправлен через Telegram API: account_id=%s, phone_code_hash=%s",
            account_id,
            phone_code_hash,
        )

        return AuthStep1Response(account_id=account_id)

    async def verify_code(
            self, session: AsyncSession, data: dict
    ) -> AuthStep2Response:
        """
        Шаг 2 авторизации: ввести SMS-код.

        Если аккаунт с 2FA — возвращает статус "2fa_required".
        Иначе — подключает аккаунт и публикует событие.
        """
        account = await self._get_account(session, data["account_id"])

        status = await self.client_manager.sign_in_with_code(data["account_id"], data["code"])

        if status == TgAuthStatus.INVALID_CODE:
            raise HTTPException(status_code=400, detail="Неверный или истёкший код подтверждения")

        if status == TgAuthStatus.CONNECTED:
            await self._update_account_info(session, account)
            self.register_message_handler(account.id)

            event = TgAccountConnected(
                account_id=account.id,
                phone=account.phone,
            )
            await self.message_bus.publish(BusTopics.TG_ACCOUNT_CONNECTED, event.to_bus_dict())

        return AuthStep2Response(account_id=data["account_id"], status=status)

    async def verify_password(
            self, session: AsyncSession, data: dict
    ) -> AuthStep3Response:
        """Шаг 3 авторизации: ввести пароль облачного шифрования (2FA)."""
        account = await self._get_account(session, data["account_id"])

        status = await self.client_manager.sign_in_with_password(
            data["account_id"], data["password"]
        )

        if status == TgAuthStatus.CONNECTED:
            await self._update_account_info(session, account)
            self.register_message_handler(account.id)

            event = TgAccountConnected(
                account_id=account.id,
                phone=account.phone,
            )
            await self.message_bus.publish(BusTopics.TG_ACCOUNT_CONNECTED, event.to_bus_dict())

        return AuthStep3Response(account_id=data["account_id"], status=status)

    async def _update_account_info(self, session: AsyncSession, account: TelegramAccount) -> None:
        """Обновляет информацию об аккаунте из Telegram API."""
        me = await self.client_manager.get_me(account.id)
        if me:
            await self.repository.update(
                session,
                account,
                {
                    "is_connected": True,
                    "first_name": me.get("first_name"),
                    "last_name": me.get("last_name"),
                    "username": me.get("username"),
                    "telegram_id": me.get("telegram_id"),
                },
            )

    async def get_active_accounts(
            self,
            session: AsyncSession,
    ) -> list[TelegramAccount]:
        """Получить активные Telegram-аккаунты."""
        return await self.repository.get_connected_accounts(session)

    async def delete_account(
            self, session: AsyncSession, account_id: uuid.UUID
    ) -> None:
        """Удалить Telegram-аккаунт."""
        account = await self._get_account(session, account_id)

        # Отключаем клиент
        await self.client_manager.disconnect_account(account_id)

        # Удаляем session-файл
        if account.session_file and os.path.exists(account.session_file + ".session"):
            os.remove(account.session_file + ".session")

        # Удаляем из БД
        await self.repository.delete(session, account)

        # Публикуем событие
        event = TgAccountDisconnected(
            account_id=account.id,
            reason="deleted",
        )
        await self.message_bus.publish(BusTopics.TG_ACCOUNT_DISCONNECTED, event.to_bus_dict())

    async def get_chats(
            self, session: AsyncSession, account_id: uuid.UUID, limit: int = 100
    ) -> list[dict]:
        """Получить все чаты аккаунта из Telegram API."""
        account = await self._get_account(session, account_id)
        if not account.is_connected:
            raise ConflictError(detail="Аккаунт не подключён")

        chats = await self.client_manager.get_chats(account_id, limit)
        settings = await self.settings_repository.get_by_account_id(session, account_id)
        whitelist = {str(value) for value in (settings.whitelist_chat_ids if settings else [])}
        return [
            {**chat, "is_in_whitelist": str(chat["id"]) in whitelist}
            for chat in chats
        ]

    async def get_messages(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
            chat_id: int,
            limit: int = 50,
            offset_id: int = 0,
    ) -> list[TgMessageReceived]:
        """Получить сообщения чата из Telegram API (on-demand)."""
        account = await self._get_account(session, account_id)
        if not account.is_connected:
            raise ConflictError(detail="Аккаунт не подключён")

        return await self.client_manager.get_messages(
            account_id, chat_id, limit=limit, offset_id=offset_id
        )

    async def _get_account(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
    ) -> TelegramAccount:
        """Получить аккаунт по ID."""
        account = await self.repository.get_by_id(session, account_id)
        if not account:
            raise NotFoundError(detail="Аккаунт не найден")
        return account

    # ── QR-авторизация ─────────────────────────────────────────────

    async def start_qr_auth(self, session: AsyncSession) -> QrStartResponse:
        """
        Шаг 1 QR-авторизации: создать QR-сессию.

        Запись в БД не создаётся. Возвращает account_id и qr_url.
        """
        account_id = uuid.uuid4()

        logger.info(
            "[tg qr auth] Старт QR-авторизации: account_id=%s",
            account_id,
        )

        result = await self.client_manager.start_qr_login(account_id)

        return QrStartResponse(
            account_id=account_id,
            qr_url=result["qr_url"],
            expires_at=result.get("expires_at"),
        )

    async def get_qr_status(self, account_id: uuid.UUID) -> QrStatusResponse:
        """Получить статус QR-сессии."""
        result = self.client_manager.get_qr_status(account_id)
        return QrStatusResponse(**result)

    async def cancel_qr_auth(self, account_id: uuid.UUID) -> None:
        """Отменить QR-авторизацию."""
        await self.client_manager.cancel_qr_login(account_id)

    async def complete_qr_auth(
            self, session: AsyncSession, account_id: uuid.UUID
    ) -> TelegramAccount:
        """
        Финализировать QR-авторизацию: создать запись в БД и опубликовать событие.
        """
        me = await self.client_manager.complete_qr_login(account_id)

        session_path = self.client_manager.get_session_path(account_id)

        account = await self.repository.create(
            session,
            {
                "id": account_id,
                "phone": me.get("phone", "") or "",
                "session_file": session_path,
                "is_connected": True,
                "first_name": me.get("first_name"),
                "last_name": me.get("last_name"),
                "username": me.get("username"),
                "telegram_id": me.get("telegram_id"),
            },
        )

        # QR-клиент уже авторизован и остаётся в реестре ClientManager.
        # Как и в SMS/2FA-сценарии, сразу подписываем его на новые сообщения.
        self.register_message_handler(account.id)

        event = TgAccountConnected(
            account_id=account.id,
            phone=account.phone,
        )
        await self.message_bus.publish(BusTopics.TG_ACCOUNT_CONNECTED, event.to_bus_dict())

        logger.info(
            "[tg qr auth] QR-авторизация завершена: account_id=%s, telegram_id=%s",
            account_id,
            me.get("telegram_id"),
        )

        return account


    async def get_chat_state(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
            chat_id: int,
    ) -> TelegramChatState:
        """
        Получить состояние чтения чата.

        Выбрасывает NotFoundError если состояние не найдено.
        """
        # Получаем состояние
        state = await self.chat_state_repository.get_by_account_and_chat(
            session, account_id, chat_id
        )
        if not state:
            raise NotFoundError(detail="Состояние чтения чата не найдено")

        return state

    async def update_last_read(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
            chat_id: int,
            message_id: int,
    ) -> TelegramChatState:
        """
        Обновить последнее прочитанное сообщение в чате.

        Использует upsert_last_read из репозитория.
        """
        # Обновляем или создаём состояние
        return await self.chat_state_repository.upsert_last_read(
            session, account_id, chat_id, message_id
        )

    async def get_all_chats_state(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
    ) -> list[TelegramChatState]:
        """
        Получить все состояния чтения чатов аккаунта.
        """
        # Получаем все состояния
        return await self.chat_state_repository.get_all_by_account(session, account_id)

    async def read_unread_messages(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
    ) -> int:
        """
        Прочитать непрочитанные сообщения для аккаунта.

        Для каждого чата с TelegramChatState:
        1. Получаем непрочитанные сообщения (message_id > last_read_message_id)
        2. Публикуем каждое сообщение в шину
        3. Обновляем состояние чтения

        Args:
            session: SQLAlchemy сессия
            account_id: ID аккаунта

        Returns:
            Количество прочитанных сообщений.
        """
        # Получаем все состояния чтения для аккаунта
        chat_states = await self.chat_state_repository.get_all_by_account(session, account_id)

        total_read = 0

        for state in chat_states:
            # Получаем непрочитанные сообщения
            unread_messages = await self.client_manager.get_messages(
                account_id=account_id,
                chat_id=state.chat_id,
                last_read_message_id=state.last_read_message_id,
            )

            if not unread_messages:
                continue

            # Публикуем каждое сообщение в шину и обновляем состояние
            for msg in unread_messages:
                await self.message_bus.publish(
                    BusTopics.TG_MESSAGE_RECEIVED,
                    msg.to_bus_dict(),
                )
                await self.chat_state_repository.upsert_last_read(
                    session=session,
                    account_id=account_id,
                    chat_id=state.chat_id,
                    message_id=msg.message_id,
                )

            total_read += len(unread_messages)
            logger.info(
                "Прочитано %d сообщений из чата %s для аккаунта %s",
                len(unread_messages),
                state.chat_id,
                account_id,
            )

        logger.info(
            "Всего прочитано %d непрочитанных сообщений для аккаунта %s",
            total_read,
            account_id,
        )
        return total_read

    async def should_read_message(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
            chat_id: int,
    ) -> bool:
        settings = await self.settings_repository.get_by_account_id(session, account_id)
        if not settings or not settings.use_whitelist:
            return True
        return str(chat_id) in {str(value) for value in (settings.whitelist_chat_ids or [])}

    async def handle_incoming_message(
            self,
            session: AsyncSession,
            account_id: uuid.UUID,
            event: NewMessage.Event,
    ) -> None:
        """
        Обработать входящее сообщение.

        Выполняет:
        1. Проверка настроек (should_read_message)
        2. Публикация события в шину
        3. Обновление состояния чтения чата
        4. Загрузка медиа в storage

        Args:
            session: SQLAlchemy async сессия
            account_id: ID аккаунта
            event: Событие NewMessage.Event
        """
        try:
            # Определяем тип чата
            should_read = await self.should_read_message(
                session,
                account_id,
                event.chat_id,
            )

            if not should_read:
                return  # Пропускаем сообщение согласно настройкам

            client = self.client_manager.get_client(account_id)

            # Извлекаем медиа из сообщения
            media = await self.client_manager.extract_media(client, event.message)
            telegram_sender = await event.get_sender()
            msg_event = TgMessageReceived(
                account_id=account_id,
                chat_id=event.chat_id,
                message_id=event.message.id,
                sender=Sender(
                    sender_id=event.sender_id,
                    username=getattr(telegram_sender, "username", None),
                    first_name=getattr(telegram_sender, "first_name", None),
                    last_name=getattr(telegram_sender, "last_name", None),
                ),
                text=event.message.text,
                media=media,
                date=event.message.date,
            )
            await self.message_bus.publish(BusTopics.TG_MESSAGE_RECEIVED, msg_event.to_bus_dict())

            # Обновляем состояние чтения чата
            await self.chat_state_repository.upsert_last_read(
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

        except asyncio.CancelledError:
            logger.warning("Обработка входящего сообщения отменена для аккаунта %s", account_id)
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Ошибка подключения при обработке сообщения для аккаунта %s: %s",
                account_id,
                e,
            )
        except Exception as e:
            logger.exception(
                "Неожиданная ошибка при обработке входящего сообщения для аккаунта %s: %s",
                account_id,
                e,
            )

    async def restore_tg_sessions(self, session: AsyncSession) -> None:
        """Восстановление подключений Telegram-аккаунтов при старте."""
        accounts = await self.repository.get_connected_accounts(session)
        for account in accounts:
            status = await self.client_manager.connect_account(account.id)
            if status:
                self.register_message_handler(account.id)

    def register_message_handler(self, account_id: uuid.UUID) -> None:
        """Регистрирует обработчик входящих сообщений для клиента."""
        client = self.client_manager.get_client(account_id)
        if client is None:
            raise ConflictError(detail="Telegram-клиент не подключён")

        @client.on(NewMessage)
        async def on_new_message(event) -> None:
            """
            Обработать входящее сообщение.
            """

            async with create_async_session() as session:
                await self.handle_incoming_message(
                    session=session,
                    account_id=account_id,
                    event=event,
                )

        logger.info("Зарегистрирован NewMessage handler: account_id=%s", account_id)
