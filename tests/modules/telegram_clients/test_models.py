"""
Тесты моделей модуля Telegram-клиентов.

Тестирование ORM-моделей: создание, валидация, ограничения БД.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.telegram_clients.models import TelegramAccount, TelegramChatState


@pytest.fixture
async def tg_account(db_session: AsyncSession) -> TelegramAccount:
    """Создаёт тестовый TelegramAccount в БД."""
    from src.modules.auth.repository import AuthRepository

    # Создаём Auth аккаунт для ForeignKey
    auth_repo = AuthRepository()
    auth_account = await auth_repo.create(
        db_session,
        {
            "identifier": "test_chat_state@example.com",
            "identifier_type": "email",
            "hashed_password": "hashed",
        },
    )

    # Создаём Telegram аккаунт
    tg_account = TelegramAccount(
        phone="+79001234567",
        session_file="/tmp/test_session_state",
        is_connected=True,
    )
    db_session.add(tg_account)
    await db_session.commit()
    await db_session.refresh(tg_account)
    return tg_account


class TestTelegramChatStateCreation:
    """Тесты создания состояния чата."""

    async def test_chat_state_creation(self, db_session: AsyncSession, tg_account: TelegramAccount):
        """Создание и сохранение состояния чата."""
        chat_state = TelegramChatState(
            account_id=tg_account.id,
            chat_id=-1001234567890,
            last_read_message_id=42,
        )

        db_session.add(chat_state)
        await db_session.commit()
        await db_session.refresh(chat_state)

        # Проверка что запись сохранилась
        result = await db_session.execute(
            select(TelegramChatState).where(TelegramChatState.id == chat_state.id)
        )
        saved_state = result.scalar_one()

        assert saved_state is not None
        assert saved_state.account_id == tg_account.id
        assert saved_state.chat_id == -1001234567890
        assert saved_state.last_read_message_id == 42
        assert saved_state.id is not None
        assert saved_state.created_at is not None
        assert saved_state.updated_at is not None

    async def test_chat_state_multiple_chats(
        self, db_session: AsyncSession, tg_account: TelegramAccount
    ):
        """Можно создать состояния для разных чатов одного аккаунта."""
        chat1 = TelegramChatState(
            account_id=tg_account.id,
            chat_id=-1001111111111,
            last_read_message_id=10,
        )
        chat2 = TelegramChatState(
            account_id=tg_account.id,
            chat_id=-1002222222222,
            last_read_message_id=20,
        )

        db_session.add_all([chat1, chat2])
        await db_session.commit()

        result = await db_session.execute(
            select(TelegramChatState).where(TelegramChatState.account_id == tg_account.id)
        )
        states = result.scalars().all()

        assert len(states) == 2
        chat_ids = {s.chat_id for s in states}
        assert -1001111111111 in chat_ids
        assert -1002222222222 in chat_ids


class TestTelegramChatStateUniqueConstraint:
    """Тесты уникальности пары (account_id, chat_id)."""

    async def test_chat_state_unique_constraint(
        self, db_session: AsyncSession, tg_account: TelegramAccount
    ):
        """Попытка создать дубликат (account_id, chat_id) вызывает ошибку IntegrityError."""
        # Создаём первую запись
        chat_state1 = TelegramChatState(
            account_id=tg_account.id,
            chat_id=-1001234567890,
            last_read_message_id=42,
        )
        db_session.add(chat_state1)
        await db_session.commit()

        # Попытка создать дубликат
        chat_state2 = TelegramChatState(
            account_id=tg_account.id,  # Тот же аккаунт
            chat_id=-1001234567890,  # Тот же chat_id
            last_read_message_id=100,
        )
        db_session.add(chat_state2)

        # Должна возникнуть ошибка уникальности
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_chat_state_different_accounts_same_chat(
        self, db_session: AsyncSession, tg_account: TelegramAccount
    ):
        """Можно создать состояния с одинаковым chat_id для разных аккаунтов."""
        from src.modules.auth.repository import AuthRepository

        # Создаём второй Auth аккаунт
        auth_repo = AuthRepository()
        auth_account2 = await auth_repo.create(
            db_session,
            {
                "identifier": "test_chat_state2@example.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )

        # Создаём второй Telegram аккаунт
        tg_account2 = TelegramAccount(
            phone="+79009876543",
            session_file="/tmp/test_session_state2",
            is_connected=True,
        )
        db_session.add(tg_account2)
        await db_session.commit()

        # Создаём состояния с одинаковым chat_id для разных аккаунтов
        chat_state1 = TelegramChatState(
            account_id=tg_account.id,
            chat_id=-1001234567890,
            last_read_message_id=42,
        )
        chat_state2 = TelegramChatState(
            account_id=tg_account2.id,
            chat_id=-1001234567890,  # Тот же chat_id, но другой account_id
            last_read_message_id=50,
        )

        db_session.add_all([chat_state1, chat_state2])
        await db_session.commit()

        result = await db_session.execute(
            select(TelegramChatState).where(TelegramChatState.chat_id == -1001234567890)
        )
        states = result.scalars().all()

        assert len(states) == 2
        account_ids = {s.account_id for s in states}
        assert tg_account.id in account_ids
        assert tg_account2.id in account_ids


class TestTelegramChatStateCascadeDelete:
    """Тесты каскадного удаления при удалении TelegramAccount."""

    async def test_chat_state_cascade_delete(
        self, db_session: AsyncSession, tg_account: TelegramAccount
    ):
        """При удалении TelegramAccount удаляются связанные состояния чатов."""
        # Создаём состояние чата
        chat_state = TelegramChatState(
            account_id=tg_account.id,
            chat_id=-1001234567890,
            last_read_message_id=42,
        )
        db_session.add(chat_state)
        await db_session.commit()

        chat_state_id = chat_state.id

        # Удаляем Telegram аккаунт
        await db_session.delete(tg_account)
        await db_session.commit()

        # Проверяем что состояние чата тоже удалилось
        result = await db_session.execute(
            select(TelegramChatState).where(TelegramChatState.id == chat_state_id)
        )
        deleted_state = result.scalar_one_or_none()

        assert deleted_state is None
