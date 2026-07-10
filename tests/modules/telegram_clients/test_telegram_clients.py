"""
Тесты модуля Telegram-клиентов: репозиторий, сервис, события, обработчики.

Telethon мокается — реальные подключения к Telegram не выполняются.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.in_memory.producer import InMemoryProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.telegram_clients.client_manager import TelegramClientManager
from src.modules.telegram_clients.models import TelegramAccount
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.schemas.events import (
    TgAccountConnected,
    TgAccountDisconnected,
    TgMessageReceived,
)
from src.modules.telegram_clients.schemas.public import (
    CodeRequest,
    PasswordRequest,
)
from src.modules.telegram_clients.service import TelegramClientService

# --- Фикстуры ---


@pytest.fixture
def tg_repository() -> TelegramAccountRepository:
    return TelegramAccountRepository()


@pytest.fixture
def message_bus() -> InMemoryProducer:
    return InMemoryProducer()


@pytest.fixture
def client_manager() -> TelegramClientManager:
    return TelegramClientManager()


@pytest.fixture
def settings_repository() -> TelegramSettingsRepository:
    return TelegramSettingsRepository()


@pytest.fixture
def chat_state_repository() -> TelegramChatStateRepository:
    return TelegramChatStateRepository()


@pytest.fixture
def tg_service(
    tg_repository: TelegramAccountRepository,
    message_bus: InMemoryProducer,
    client_manager: TelegramClientManager,
    settings_repository: TelegramSettingsRepository,
    chat_state_repository: TelegramChatStateRepository,
) -> TelegramClientService:
    return TelegramClientService(
        repository=tg_repository,
        message_bus=message_bus,
        client_manager=client_manager,
        settings_repository=settings_repository,
        chat_state_repository=chat_state_repository,
    )


@pytest.fixture
async def existing_auth_id(db_session: AsyncSession) -> uuid.UUID:
    """Создаёт AuthAccount и возвращает его ID."""
    from src.modules.auth.repository import AuthRepository

    repo = AuthRepository()
    account = await repo.create(
        db_session,
        {
            "identifier": "tg_test@test.com",
            "identifier_type": "email",
            "hashed_password": "hashed",
        },
    )
    return account.id


@pytest.fixture
async def other_auth_id(db_session: AsyncSession) -> uuid.UUID:
    """Создаёт второй AuthAccount (чужой пользователь)."""
    from src.modules.auth.repository import AuthRepository

    repo = AuthRepository()
    account = await repo.create(
        db_session,
        {
            "identifier": "other_tg@test.com",
            "identifier_type": "email",
            "hashed_password": "hashed",
        },
    )
    return account.id


@pytest.fixture
async def tg_account(db_session: AsyncSession, existing_auth_id: uuid.UUID) -> TelegramAccount:
    """Создаёт тестовый TelegramAccount в БД."""
    repo = TelegramAccountRepository()
    account = await repo.create(
        db_session,
        {
            "auth_id": existing_auth_id,
            "phone": "+79001234567",
            "session_file": "/tmp/test_session",
            "is_connected": False,
        },
    )
    return account


@pytest.fixture
async def connected_tg_account(
    db_session: AsyncSession, existing_auth_id: uuid.UUID
) -> TelegramAccount:
    """Создаёт подключённый TelegramAccount в БД."""
    repo = TelegramAccountRepository()
    account = await repo.create(
        db_session,
        {
            "auth_id": existing_auth_id,
            "phone": "+79009999999",
            "session_file": "/tmp/test_connected_session",
            "is_connected": True,
            "first_name": "Тест",
            "telegram_id": 123456789,
        },
    )
    return account


# --- Тесты репозитория ---


class TestTelegramAccountRepository:
    """Тесты репозитория Telegram-аккаунтов."""

    async def test_get_by_auth_id(
        self,
        db_session: AsyncSession,
        tg_repository: TelegramAccountRepository,
        existing_auth_id: uuid.UUID,
    ):
        """Поиск аккаунтов по auth_id."""
        await tg_repository.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79001111111",
                "session_file": "/tmp/s1",
            },
        )
        results, total = await tg_repository.get_by_auth_id(db_session, existing_auth_id)
        assert len(results) == 1
        assert results[0].phone == "+79001111111"
        assert total == 1

    async def test_get_by_auth_id_empty(
        self,
        db_session: AsyncSession,
        tg_repository: TelegramAccountRepository,
    ):
        """Пустой результат при поиске несуществующего auth_id."""
        results, total = await tg_repository.get_by_auth_id(db_session, uuid.uuid4())
        assert len(results) == 0
        assert total == 0

    async def test_get_connected_accounts(
        self,
        db_session: AsyncSession,
        tg_repository: TelegramAccountRepository,
        existing_auth_id: uuid.UUID,
    ):
        """Поолько подключённые аккаунты."""
        await tg_repository.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79002222222",
                "session_file": "/tmp/s2",
                "is_connected": True,
            },
        )
        await tg_repository.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79003333333",
                "session_file": "/tmp/s3",
                "is_connected": False,
            },
        )
        results = await tg_repository.get_connected_accounts(db_session)
        assert len(results) == 1
        assert results[0].phone == "+79002222222"


# --- Тесты сервиса: управление аккаунтами ---


class TestTelegramClientServiceGetAccounts:
    """Тесты получения списка аккаунтов."""

    async def test_get_accounts(
        self,
        db_session: AsyncSession,
        tg_service: TelegramClientService,
        existing_auth_id: uuid.UUID,
    ):
        """Возвращает аккаунты текущего пользователя."""
        repo = TelegramAccountRepository()
        await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79004444444",
                "session_file": "/tmp/s4",
            },
        )
        accounts, total = await tg_service.get_accounts(db_session, existing_auth_id)
        assert len(accounts) == 1
        assert accounts[0].phone == "+79004444444"
        assert total == 1

    async def test_get_accounts_other_user_empty(
        self,
        db_session: AsyncSession,
        tg_service: TelegramClientService,
        existing_auth_id: uuid.UUID,
        other_auth_id: uuid.UUID,
    ):
        """Не возвращает аккаунты другого пользователя."""
        repo = TelegramAccountRepository()
        await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79005555555",
                "session_file": "/tmp/s5",
            },
        )
        accounts, total = await tg_service.get_accounts(db_session, other_auth_id)
        assert len(accounts) == 0
        assert total == 0


class TestTelegramClientServiceDeleteAccount:
    """Тесты удаления аккаунта."""

    async def test_delete_account(
        self,
        db_session: AsyncSession,
        tg_service: TelegramClientService,
        tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """Успешное удаление аккаунта."""
        await tg_service.delete_account(db_session, tg_account.id, existing_auth_id)
        found = await tg_service.repository.get_by_id(db_session, tg_account.id)
        assert found is None

    async def test_delete_account_not_found(
        self,
        db_session: AsyncSession,
        tg_service: TelegramClientService,
        existing_auth_id: uuid.UUID,
    ):
        """Удаление несуществующего аккаунта — NotFoundError."""
        with pytest.raises(NotFoundError):
            await tg_service.delete_account(db_session, uuid.uuid4(), existing_auth_id)

    async def test_delete_account_wrong_user(
        self,
        db_session: AsyncSession,
        tg_service: TelegramClientService,
        tg_account: TelegramAccount,
        other_auth_id: uuid.UUID,
    ):
        """Удаление чужого аккаунта — NotFoundError."""
        with pytest.raises(NotFoundError):
            await tg_service.delete_account(db_session, tg_account.id, other_auth_id)

    async def test_delete_account_publishes_event(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """При удалении публикуется событие tg.account.disconnected."""
        published = []

        class MockBus:
            async def publish(self, topic, message):
                published.append((topic, message))

        repo = TelegramAccountRepository()
        manager = TelegramClientManager()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79006666666",
                "session_file": "/tmp/s6",
            },
        )

        await service.delete_account(db_session, account.id, existing_auth_id)

        assert len(published) == 1
        assert published[0][0] == BusTopics.TG_ACCOUNT_DISCONNECTED
        assert published[0][1]["reason"] == "deleted"


# --- Тесты сервиса: авторизация ---


class TestTelegramClientServiceAuth:
    """Тесты авторизации с моком ClientManager."""

    async def test_verify_code_wrong_user(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
        other_auth_id: uuid.UUID,
    ):
        """Ввод кода для чужого аккаунта — NotFoundError."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = CodeRequest(account_id=tg_account.id, code="12345")
        with pytest.raises(NotFoundError):
            await service.verify_code(db_session, data.model_dump(), other_auth_id)

    async def test_verify_password_wrong_user(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
        other_auth_id: uuid.UUID,
    ):
        """Ввод 2FA пароля для чужого аккаунта — NotFoundError."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = PasswordRequest(account_id=tg_account.id, password="pass")
        with pytest.raises(NotFoundError):
            await service.verify_password(db_session, data.model_dump(), other_auth_id)

    async def test_verify_code_connected_publishes_event(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """При успешном входе по коду публикуется событие tg.account.connected."""
        published = []

        class MockBus:
            async def publish(self, topic, message):
                published.append((topic, message))

        # Мокаем client_manager.sign_in_with_code → "connected"
        manager = TelegramClientManager()
        manager.sign_in_with_code = AsyncMock(return_value="connected")
        manager.get_me = AsyncMock(
            return_value={
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "telegram_id": 999888777,
            }
        )

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = CodeRequest(account_id=tg_account.id, code="12345")
        result = await service.verify_code(db_session, data.model_dump(), existing_auth_id)

        assert result.status == "connected"
        assert len(published) == 1
        assert published[0][0] == BusTopics.TG_ACCOUNT_CONNECTED

    async def test_verify_code_2fa_required(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """Если аккаунт с 2FA — возвращается статус 2fa_required."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        manager.sign_in_with_code = AsyncMock(return_value="2fa_required")

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = CodeRequest(account_id=tg_account.id, code="12345")
        result = await service.verify_code(db_session, data.model_dump(), existing_auth_id)

        assert result.status == "2fa_required"

    async def test_verify_password_connected(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """Успешный вход по 2FA паролю."""
        published = []

        class MockBus:
            async def publish(self, topic, message):
                published.append((topic, message))

        manager = TelegramClientManager()
        manager.sign_in_with_password = AsyncMock(return_value="connected")
        manager.get_me = AsyncMock(
            return_value={
                "first_name": "Test",
                "last_name": None,
                "username": None,
                "telegram_id": 111222333,
            }
        )

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = PasswordRequest(account_id=tg_account.id, password="cloudpass")
        result = await service.verify_password(db_session, data.model_dump(), existing_auth_id)

        assert result.status == "connected"
        assert len(published) == 1
        assert published[0][0] == BusTopics.TG_ACCOUNT_CONNECTED


# --- Тесты сервиса: чаты и сообщения ---


class TestTelegramClientServiceChatsMessages:
    """Тесты получения чатов и сообщений."""

    async def test_get_chats_wrong_user(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
        other_auth_id: uuid.UUID,
    ):
        """Получение чатов чужого аккаунта — NotFoundError."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        with pytest.raises(NotFoundError):
            await service.get_chats(db_session, connected_tg_account.id, other_auth_id)

    async def test_get_chats_not_connected(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """Получение чатов отключённого аккаунта — ConflictError."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        with pytest.raises(ConflictError):
            await service.get_chats(db_session, tg_account.id, existing_auth_id)

    async def test_get_messages_not_connected(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """Получение сообщений отключённого аккаунта — ConflictError."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        with pytest.raises(ConflictError):
            await service.get_messages(
                db_session, tg_account.id, chat_id=123, auth_id=existing_auth_id
            )

    async def test_get_chats_success(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """Успешное получение чатов подключённого аккаунта."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        manager.get_chats = AsyncMock(
            return_value=[
                {"id": 1, "name": "Chat1", "chat_type": "private", "username": "u1"},
            ]
        )

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        result = await service.get_chats(db_session, connected_tg_account.id, existing_auth_id)
        assert len(result) == 1
        assert result[0]["name"] == "Chat1"

    async def test_get_messages_success(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
        existing_auth_id: uuid.UUID,
    ):
        """Успешное получение сообщений подключённого аккаунта."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        manager.get_messages = AsyncMock(
            return_value=[
                {
                    "id": 42,
                    "chat_id": 1,
                    "sender_id": 100,
                    "text": "Hi",
                    "media": [],
                    "date": "2026-01-01T00:00:00Z",
                },
            ]
        )

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        result = await service.get_messages(
            db_session, connected_tg_account.id, chat_id=1, auth_id=existing_auth_id
        )
        assert len(result) == 1
        assert result[0]["text"] == "Hi"


# --- Тесты событий ---


class TestTgEvents:
    """Тесты сериализации событий шины."""

    def test_tg_message_received_to_bus_dict(self):
        event = TgMessageReceived(
            account_id=uuid.uuid4(),
            chat_id=-1001234567890,
            message_id=42,
            sender_id=123456,
            text="Привет!",
            media=[{"telegram_id": 123, "type": "photo"}],
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "tg.message.received"
        assert data["chat_id"] == -1001234567890
        assert data["message_id"] == 42
        assert data["text"] == "Привет!"
        assert len(data["media"]) == 1
        assert data["media"][0]["type"] == "photo"

    def test_tg_account_connected_to_bus_dict(self):
        event = TgAccountConnected(
            account_id=uuid.uuid4(),
            auth_id=uuid.uuid4(),
            phone="+79001234567",
            telegram_id=999888,
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "tg.account.connected"
        assert data["phone"] == "+79001234567"
        assert data["telegram_id"] == 999888

    def test_tg_account_disconnected_to_bus_dict(self):
        event = TgAccountDisconnected(
            account_id=uuid.uuid4(),
            auth_id=uuid.uuid4(),
            reason="error",
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "tg.account.disconnected"
        assert data["reason"] == "error"


# --- Тесты обработчиков ---


class TestTgHandlers:
    """Тесты обработчиков шины модуля telegram_clients."""

    async def test_handle_send_message_success(self):
        """Обработчик отправляет сообщение через client_manager."""
        from src.modules.telegram_clients.handlers import register_handlers

        bus = InMemoryProducer()
        manager = MagicMock()
        manager.send_message = AsyncMock()

        register_handlers(bus, manager)

        account_id = str(uuid.uuid4())
        await bus.publish(
            BusTopics.TG_MESSAGE_SEND,
            {
                "account_id": account_id,
                "chat_id": -100123,
                "text": "Тест",
            },
        )

        import asyncio

        await asyncio.sleep(0.05)

        manager.send_message.assert_called_once_with(uuid.UUID(account_id), -100123, "Тест")

    async def test_handle_send_message_missing_fields(self):
        """Обработчик игнорирует сообщение с неполными данными."""
        from src.modules.telegram_clients.handlers import register_handlers

        bus = InMemoryProducer()
        manager = MagicMock()
        manager.send_message = AsyncMock()

        register_handlers(bus, manager)

        await bus.publish(
            BusTopics.TG_MESSAGE_SEND,
            {
                "account_id": str(uuid.uuid4()),
                # chat_id отсутствует
                "text": "Тест",
            },
        )

        import asyncio

        await asyncio.sleep(0.05)

        manager.send_message.assert_not_called()


# --- Тесты сервиса: состояние чтения чатов ---


class TestTelegramClientServiceChatState:
    """Тесты методов управления состоянием чтения чатов."""

    async def test_get_chat_state_not_found(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """Получение несуществующего состояния — NotFoundError."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём аккаунт
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79007777777",
                "session_file": "/tmp/s7",
            },
        )

        # Пытаемся получить несуществующее состояние
        with pytest.raises(NotFoundError):
            await service.get_chat_state(db_session, account.id, existing_auth_id, chat_id=123)

    async def test_update_last_read_create_and_update(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """Создание и обновление состояния чтения."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём аккаунт
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79008888888",
                "session_file": "/tmp/s8",
            },
        )

        # Создаём состояние
        chat_id = 456
        message_id = 100
        state = await service.update_last_read(
            db_session, account.id, existing_auth_id, chat_id, message_id
        )

        assert state.account_id == account.id
        assert state.chat_id == chat_id
        assert state.last_read_message_id == message_id

        # Обновляем состояние
        new_message_id = 200
        updated_state = await service.update_last_read(
            db_session, account.id, existing_auth_id, chat_id, new_message_id
        )

        assert updated_state.account_id == account.id
        assert updated_state.chat_id == chat_id
        assert updated_state.last_read_message_id == new_message_id

    async def test_update_last_read_multiple_chats(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """Обновление состояния для нескольких чатов."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём аккаунт
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79009999999",
                "session_file": "/tmp/s9",
            },
        )

        # Обновляем состояния для разных чатов
        await service.update_last_read(db_session, account.id, existing_auth_id, 1, 10)
        await service.update_last_read(db_session, account.id, existing_auth_id, 2, 20)
        await service.update_last_read(db_session, account.id, existing_auth_id, 3, 30)

        # Получаем все состояния
        all_states = await service.get_all_chats_state(db_session, account.id, existing_auth_id)

        assert len(all_states) == 3
        chat_ids = {state.chat_id for state in all_states}
        assert chat_ids == {1, 2, 3}

    async def test_get_all_chats_state(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """Получение всех состояний чтения аккаунта."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём аккаунт
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79001112222",
                "session_file": "/tmp/s10",
            },
        )

        # Создаём несколько состояний
        await service.update_last_read(db_session, account.id, existing_auth_id, 100, 1)
        await service.update_last_read(db_session, account.id, existing_auth_id, 101, 2)

        # Получаем все состояния
        states = await service.get_all_chats_state(db_session, account.id, existing_auth_id)

        assert len(states) == 2
        assert all(state.account_id == account.id for state in states)

    async def test_get_chat_state_wrong_user(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
        other_auth_id: uuid.UUID,
    ):
        """Получение состояния чужого аккаунта — NotFoundError."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём аккаунт для existing_auth_id
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79003334444",
                "session_file": "/tmp/s11",
            },
        )

        # Создаём состояние
        await service.update_last_read(db_session, account.id, existing_auth_id, 200, 50)

        # Пытаемся получить состояние от имени other_auth_id
        with pytest.raises(NotFoundError):
            await service.get_chat_state(db_session, account.id, other_auth_id, chat_id=200)

    async def test_update_last_read_wrong_user(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
        other_auth_id: uuid.UUID,
    ):
        """Обновление состояния чужого аккаунта — NotFoundError."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём аккаунт для existing_auth_id
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79005556666",
                "session_file": "/tmp/s12",
            },
        )

        # Пытаемся обновить состояние от имени other_auth_id
        with pytest.raises(NotFoundError):
            await service.update_last_read(
                db_session, account.id, other_auth_id, chat_id=300, message_id=100
            )

    async def test_get_all_chats_state_wrong_user(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
        other_auth_id: uuid.UUID,
    ):
        """Получение всех состояний чужого аккаунта — NotFoundError."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём аккаунт для existing_auth_id
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79007778888",
                "session_file": "/tmp/s13",
            },
        )

        # Создаём состояние
        await service.update_last_read(db_session, account.id, existing_auth_id, 400, 150)

        # Пытаемся получить все состояния от имени other_auth_id
        with pytest.raises(NotFoundError):
            await service.get_all_chats_state(db_session, account.id, other_auth_id)

    async def test_get_chat_state_not_connected_account(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """Получение состояния для неподключенного аккаунта — работает нормально."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramClientService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        # Создаём неподключенный аккаунт
        account = await repo.create(
            db_session,
            {
                "auth_id": existing_auth_id,
                "phone": "+79009990000",
                "session_file": "/tmp/s14",
                "is_connected": False,
            },
        )

        # Создаём состояние
        state = await service.update_last_read(
            db_session, account.id, existing_auth_id, chat_id=500, message_id=25
        )

        assert state.account_id == account.id
        assert state.chat_id == 500
        assert state.last_read_message_id == 25

        # Получаем состояние
        retrieved_state = await service.get_chat_state(
            db_session, account.id, existing_auth_id, chat_id=500
        )

        assert retrieved_state.account_id == account.id
        assert retrieved_state.last_read_message_id == 25
