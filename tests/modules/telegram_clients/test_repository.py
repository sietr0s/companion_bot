"""
Тесты репозитория TelegramChatStateRepository.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.telegram_clients.models import TelegramAccount, TelegramChatState
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
)

# --- Фикстуры ---


@pytest.fixture
def chat_state_repository() -> TelegramChatStateRepository:
    return TelegramChatStateRepository()


@pytest.fixture
async def test_account(db_session: AsyncSession) -> TelegramAccount:
    """Создаёт тестовый TelegramAccount."""
    repo = TelegramAccountRepository()
    account = await repo.create(
        db_session,
        {
            "auth_id": uuid.uuid4(),
            "phone": "+79001234567",
            "session_file": "/tmp/test_session",
            "is_connected": True,
        },
    )
    return account


@pytest.fixture
async def chat_state(
    db_session: AsyncSession,
    chat_state_repository: TelegramChatStateRepository,
    test_account: TelegramAccount,
) -> TelegramChatState:
    """Создаёт тестовое состояние чата."""
    state = await chat_state_repository.upsert_last_read(
        db_session,
        test_account.id,
        chat_id=-1001234567890,
        message_id=100,
    )
    return state


# --- Тесты ---


class TestTelegramChatStateRepository:
    """Тесты репозитория TelegramChatStateRepository."""

    async def test_get_by_account_and_chat(
        self,
        db_session: AsyncSession,
        chat_state_repository: TelegramChatStateRepository,
        chat_state: TelegramChatState,
        test_account: TelegramAccount,
    ):
        """Получение существующей записи по account_id и chat_id."""
        result = await chat_state_repository.get_by_account_and_chat(
            db_session,
            test_account.id,
            chat_state.chat_id,
        )

        assert result is not None
        assert result.account_id == test_account.id
        assert result.chat_id == chat_state.chat_id
        assert result.last_read_message_id == 100

    async def test_get_by_account_and_chat_not_found(
        self,
        db_session: AsyncSession,
        chat_state_repository: TelegramChatStateRepository,
        test_account: TelegramAccount,
    ):
        """Получение несуществующей записи возвращает None."""
        result = await chat_state_repository.get_by_account_and_chat(
            db_session,
            test_account.id,
            chat_id=-999888777666,
        )

        assert result is None

    async def test_upsert_last_read_create(
        self,
        db_session: AsyncSession,
        chat_state_repository: TelegramChatStateRepository,
        test_account: TelegramAccount,
    ):
        """upsert_last_read создаёт новую запись если её нет."""
        chat_id = -111222333444
        message_id = 42

        result = await chat_state_repository.upsert_last_read(
            db_session,
            test_account.id,
            chat_id,
            message_id,
        )

        assert result is not None
        assert result.account_id == test_account.id
        assert result.chat_id == chat_id
        assert result.last_read_message_id == message_id

        # Проверяем что запись действительно сохранилась
        found = await chat_state_repository.get_by_account_and_chat(
            db_session, test_account.id, chat_id
        )
        assert found is not None
        assert found.last_read_message_id == message_id

    async def test_upsert_last_read_update(
        self,
        db_session: AsyncSession,
        chat_state_repository: TelegramChatStateRepository,
        test_account: TelegramAccount,
        chat_state: TelegramChatState,
    ):
        """upsert_last_read обновляет существующую запись."""
        # Изначально last_read_message_id = 100 (из фикстуры)
        new_message_id = 999

        result = await chat_state_repository.upsert_last_read(
            db_session,
            test_account.id,
            chat_state.chat_id,
            new_message_id,
        )

        assert result is not None
        assert result.account_id == test_account.id
        assert result.chat_id == chat_state.chat_id
        assert result.last_read_message_id == new_message_id

        # Проверяем что запись обновилась в БД
        found = await chat_state_repository.get_by_account_and_chat(
            db_session, test_account.id, chat_state.chat_id
        )
        assert found is not None
        assert found.last_read_message_id == new_message_id

    async def test_get_all_by_account(
        self,
        db_session: AsyncSession,
        chat_state_repository: TelegramChatStateRepository,
        test_account: TelegramAccount,
    ):
        """Получение всех состояний для аккаунта."""
        # Создаём несколько состояний для этого аккаунта
        await chat_state_repository.upsert_last_read(
            db_session, test_account.id, chat_id=-100001, message_id=1
        )
        await chat_state_repository.upsert_last_read(
            db_session, test_account.id, chat_id=-100002, message_id=2
        )
        await chat_state_repository.upsert_last_read(
            db_session, test_account.id, chat_id=-100003, message_id=3
        )

        result = await chat_state_repository.get_all_by_account(db_session, test_account.id)

        assert len(result) == 3
        chat_ids = {state.chat_id for state in result}
        assert -100001 in chat_ids
        assert -100002 in chat_ids
        assert -100003 in chat_ids

    async def test_get_all_by_account_empty(
        self,
        db_session: AsyncSession,
        chat_state_repository: TelegramChatStateRepository,
        test_account: TelegramAccount,
    ):
        """Получение всех состояний для аккаунта без состояний."""
        result = await chat_state_repository.get_all_by_account(db_session, test_account.id)

        assert len(result) == 0

    async def test_get_all_by_account_other_account(
        self,
        db_session: AsyncSession,
        chat_state_repository: TelegramChatStateRepository,
        test_account: TelegramAccount,
    ):
        """get_all_by_account не возвращает состояния другого аккаунта."""
        # Создаём состояние для этого аккаунта
        await chat_state_repository.upsert_last_read(
            db_session, test_account.id, chat_id=-100001, message_id=1
        )

        # Создаём аккаунт и состояние для другого пользователя
        other_account = await TelegramAccountRepository().create(
            db_session,
            {
                "auth_id": uuid.uuid4(),
                "phone": "+79009998877",
                "session_file": "/tmp/other_session",
                "is_connected": True,
            },
        )
        await chat_state_repository.upsert_last_read(
            db_session, other_account.id, chat_id=-100002, message_id=2
        )

        # Получаем состояния только для test_account
        result = await chat_state_repository.get_all_by_account(db_session, test_account.id)

        assert len(result) == 1
        assert result[0].chat_id == -100001
