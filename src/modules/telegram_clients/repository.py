"""
Репозиторий Telegram-аккаунтов и настроек.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.telegram_clients.models import (
    TelegramAccount,
    TelegramChatState,
    TelegramSettings,
)


class TelegramAccountRepository(BaseRepository[TelegramAccount]):
    """Репозиторий для работы с Telegram-аккаунтами."""

    def __init__(self) -> None:
        super().__init__(TelegramAccount)

    async def get_connected_accounts(self, session: AsyncSession) -> list[TelegramAccount]:
        """Получить все подключённые аккаунты (для загрузки при старте)."""
        stmt = select(TelegramAccount).where(TelegramAccount.is_connected.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())


class TelegramSettingsRepository(BaseRepository[TelegramSettings]):
    """Репозиторий для работы с настройками Telegram-аккаунтов."""

    def __init__(self) -> None:
        super().__init__(TelegramSettings)

    async def get_by_account_id(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> TelegramSettings | None:
        """Получить настройки по account_id."""
        stmt = select(self.model).where(self.model.account_id == account_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class TelegramChatStateRepository(BaseRepository[TelegramChatState]):
    """Репозиторий для работы с состояниями чтения чатов Telegram."""

    def __init__(self) -> None:
        super().__init__(TelegramChatState)

    async def get_by_account_and_chat(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        chat_id: int,
    ) -> TelegramChatState | None:
        """
        Получить состояние чтения чата для пары (account_id, chat_id).

        Returns:
            TelegramChatState | None: Состояние или None если не найдено.
        """
        stmt = select(self.model).where(
            self.model.account_id == account_id,
            self.model.chat_id == chat_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_last_read(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        chat_id: int,
        message_id: int,
    ) -> TelegramChatState:
        """
        Создать или обновить состояние чтения чата.

        Если запись существует — обновляет last_read_message_id.
        Если записи нет — создаёт новую.

        Returns:
            TelegramChatState: Состояние после операции.
        """
        # Пытаемся найти существующую запись
        existing = await self.get_by_account_and_chat(session, account_id, chat_id)
        if existing:
            return await self.update(session, existing, {"last_read_message_id": message_id})
        return await self.create(
            session,
            {
                "account_id": account_id,
                "chat_id": chat_id,
                "last_read_message_id": message_id,
            },
        )

    async def get_all_by_account(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
    ) -> list[TelegramChatState]:
        """
        Получить все состояния чтения чатов для аккаунта.

        Returns:
            list[TelegramChatState]: Список состояний.
        """
        stmt = select(self.model).where(self.model.account_id == account_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
