"""
Сервис модуля Telegram-клиентов.

Содержит бизнес-логику авторизации, управления аккаунтами,
получения чатов и сообщений. Делегирует работу с Telethon
клиент-менеджеру, а персистентность — репозиторию.
"""

import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter
from src.base.service import BaseService
from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.telegram_clients.client_manager import TelegramClientManager
from src.modules.telegram_clients.constants import TgAuthStatus
from src.modules.telegram_clients.models import (
    TelegramAccount,
    TelegramChatState,
    TelegramSettings,
)
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.schemas.events import (
    TgAccountConnected,
    TgAccountDisconnected,
)
from src.modules.telegram_clients.schemas.public import (
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
)


class TelegramClientService(BaseService[TelegramAccountRepository]):
    """
    Сервис управления Telegram-аккаунтами.

    Координирует работу репозитория (БД) и клиент-менеджера (Telethon).
    """

    def __init__(
        self,
        repository: TelegramAccountRepository,
        message_bus: MessageBus,
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
        self, session: AsyncSession, data: dict, auth_id: uuid.UUID
    ) -> AuthStep1Response:
        """
        Шаг 1 авторизации: отправить SMS-код на номер.

        Создаёт запись в БД и инициирует отправку кода через Telethon.
        """
        # Создаём запись аккаунта
        account_id = uuid.uuid4()
        session_path = self.client_manager._get_session_path(account_id)

        await self.repository.create(
            session,
            {
                "id": account_id,
                "auth_id": auth_id,
                "phone": data["phone"],
                "session_file": session_path,
                "is_connected": False,
            },
        )

        # Отправляем код через Telethon
        await self.client_manager.send_code(data["phone"], account_id)

        return AuthStep1Response(account_id=account_id)

    async def verify_code(
        self, session: AsyncSession, data: dict, auth_id: uuid.UUID
    ) -> AuthStep2Response:
        """
        Шаг 2 авторизации: ввести SMS-код.

        Если аккаунт с 2FA — возвращает статус "2fa_required".
        Иначе — подключает аккаунт и публикует событие.
        """
        account = await self._get_user_account(session, data["account_id"], auth_id)

        status = await self.client_manager.sign_in_with_code(data["account_id"], data["code"])

        if status == TgAuthStatus.CONNECTED:
            # Обновляем данные аккаунта из Telegram
            await self._update_account_info(session, account)

            # Публикуем событие
            event = TgAccountConnected(
                account_id=account.id,
                auth_id=account.auth_id,
                phone=account.phone,
            )
            await self.message_bus.publish(BusTopics.TG_ACCOUNT_CONNECTED, event.to_bus_dict())

        return AuthStep2Response(account_id=data["account_id"], status=status)

    async def verify_password(
        self, session: AsyncSession, data: dict, auth_id: uuid.UUID
    ) -> AuthStep3Response:
        """Шаг 3 авторизации: ввести пароль облачного шифрования (2FA)."""
        account = await self._get_user_account(session, data["account_id"], auth_id)

        status = await self.client_manager.sign_in_with_password(
            data["account_id"], data["password"]
        )

        if status == TgAuthStatus.CONNECTED:
            await self._update_account_info(session, account)

            event = TgAccountConnected(
                account_id=account.id,
                auth_id=account.auth_id,
                phone=account.phone,
            )
            await self.message_bus.publish(BusTopics.TG_ACCOUNT_CONNECTED, event.to_bus_dict())

        return AuthStep3Response(account_id=data["account_id"])

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

    async def get_accounts(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
        filters: list[Filter] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[TelegramAccount], int]:
        """Получить все Telegram-аккаунты пользователя с фильтрацией и пагинацией."""
        return await self.repository.get_by_auth_id(session, auth_id, filters, skip, limit)

    async def delete_account(
        self, session: AsyncSession, account_id: uuid.UUID, auth_id: uuid.UUID
    ) -> None:
        """Удалить Telegram-аккаунт."""
        account = await self.repository.get_by_id(session, account_id)
        if not account:
            raise NotFoundError(detail="Аккаунт не найден")
        if account.auth_id != auth_id:
            raise NotFoundError(detail="Аккаунт не найден")

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
            auth_id=account.auth_id,
            reason="deleted",
        )
        await self.message_bus.publish(BusTopics.TG_ACCOUNT_DISCONNECTED, event.to_bus_dict())

    async def get_chats(
        self, session: AsyncSession, account_id: uuid.UUID, auth_id: uuid.UUID, limit: int = 100
    ) -> list[dict]:
        """Получить все чаты аккаунта из Telegram API."""
        account = await self._get_user_account(session, account_id, auth_id)
        if not account.is_connected:
            raise ConflictError(detail="Аккаунт не подключён")

        return await self.client_manager.get_chats(account_id, limit)

    async def get_messages(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        chat_id: int,
        auth_id: uuid.UUID,
        limit: int = 50,
        offset_id: int = 0,
    ) -> list[dict]:
        """Получить сообщения чата из Telegram API (on-demand)."""
        account = await self._get_user_account(session, account_id, auth_id)
        if not account.is_connected:
            raise ConflictError(detail="Аккаунт не подключён")

        return await self.client_manager.get_messages(
            account_id, chat_id, limit=limit, offset_id=offset_id
        )

    async def _get_user_account(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        auth_id: uuid.UUID,
    ) -> TelegramAccount:
        """Получить аккаунт с проверкой принадлежности пользователю."""
        account = await self.repository.get_by_id(session, account_id)
        if not account or account.auth_id != auth_id:
            raise NotFoundError(detail="Аккаунт не найден")
        return account

    # Методы для работы с настройками

    async def get_settings(self, session: AsyncSession, account_id: uuid.UUID) -> TelegramSettings:
        """Получить или создать настройки по умолчанию для аккаунта."""

        settings = await self.settings_repository.get_by_account_id(session, account_id)
        if not settings:
            return await self._create_default_settings(session, account_id)
        return settings

    async def _create_default_settings(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> TelegramSettings:
        """Создать настройки по умолчанию."""

        default_data = {
            "account_id": account_id,
            "read_groups": True,
            "read_personal": True,
            "read_channels": True,
            "whitelist_chat_ids": [],
        }
        return await self.settings_repository.create(session, default_data)

    async def update_settings(
        self, session: AsyncSession, account_id: uuid.UUID, data: dict
    ) -> TelegramSettings:
        """Обновить настройки аккаунта."""

        settings = await self.settings_repository.get_by_account_id(session, account_id)
        if not settings:
            return await self._create_default_settings(session, account_id)

        update_data = {k: v for k, v in data.items() if v is not None}
        return await self.settings_repository.update(session, settings, update_data)

    async def delete_settings(self, session: AsyncSession, account_id: uuid.UUID) -> None:
        """Удалить настройки аккаунта."""

        settings = await self.settings_repository.get_by_account_id(session, account_id)
        if settings:
            await self.settings_repository.delete(session, settings.id)

    # Методы для работы с состоянием чтения чатов

    async def get_chat_state(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        auth_id: uuid.UUID,
        chat_id: int,
    ) -> TelegramChatState:
        """
        Получить состояние чтения чата.

        Проверяет принадлежность аккаунта пользователю.
        Выбрасывает NotFoundError если состояние не найдено.
        """
        # Проверяем принадлежность аккаунта пользователю
        await self._get_user_account(session, account_id, auth_id)

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
        auth_id: uuid.UUID,
        chat_id: int,
        message_id: int,
    ) -> TelegramChatState:
        """
        Обновить последнее прочитанное сообщение в чате.

        Проверяет принадлежность аккаунта пользователю.
        Использует upsert_last_read из репозитория.
        """
        # Проверяем принадлежность аккаунта пользователю
        await self._get_user_account(session, account_id, auth_id)

        # Обновляем или создаём состояние
        return await self.chat_state_repository.upsert_last_read(
            session, account_id, chat_id, message_id
        )

    async def get_all_chats_state(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        auth_id: uuid.UUID,
    ) -> list[TelegramChatState]:
        """
        Получить все состояния чтения чатов аккаунта.

        Проверяет принадлежность аккаунта пользователю.
        """
        # Проверяем принадлежность аккаунта пользователю
        await self._get_user_account(session, account_id, auth_id)

        # Получаем все состояния
        return await self.chat_state_repository.get_all_by_account(session, account_id)
