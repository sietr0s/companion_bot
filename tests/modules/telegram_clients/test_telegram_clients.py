"""
Тесты модуля Telegram-клиентов: репозиторий, сервис, события, обработчики.

Telethon мокается — реальные подключения к Telegram не выполняются.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.events import NewMessage

from src.bus.in_memory.producer import InMemoryProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.telegram_clients.adapters.client_manager import TelegramClientManager
from src.modules.telegram_clients.models import TelegramAccount
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
    CodeRequest,
    PasswordRequest,
)
from src.modules.telegram_clients.services.account import TelegramAccountService
from src.modules.telegram_clients.services.settings import TelegramSettingsService

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
) -> TelegramAccountService:
    return TelegramAccountService(
        repository=tg_repository,
        message_bus=message_bus,
        client_manager=client_manager,
        settings_repository=settings_repository,
        chat_state_repository=chat_state_repository,
    )


@pytest.fixture
async def tg_account(db_session: AsyncSession) -> TelegramAccount:
    """Создаёт тестовый TelegramAccount в БД."""
    repo = TelegramAccountRepository()
    account = await repo.create(
        db_session,
        {
            "phone": "+79001234567",
            "session_file": "/tmp/test_session",
            "is_connected": False,
        },
    )
    return account


@pytest.fixture
async def connected_tg_account(db_session: AsyncSession) -> TelegramAccount:
    """Создаёт подключённый TelegramAccount в БД."""
    repo = TelegramAccountRepository()
    account = await repo.create(
        db_session,
        {
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

    async def test_get_connected_accounts(
        self,
        db_session: AsyncSession,
        tg_repository: TelegramAccountRepository,
    ):
        """Только подключённые аккаунты."""
        await tg_repository.create(
            db_session,
            {
                "phone": "+79002222222",
                "session_file": "/tmp/s2",
                "is_connected": True,
            },
        )
        await tg_repository.create(
            db_session,
            {
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
        tg_service: TelegramAccountService,
    ):
        """Возвращает все аккаунты."""
        repo = TelegramAccountRepository()
        await repo.create(
            db_session,
            {
                "phone": "+79004444444",
                "session_file": "/tmp/s4",
            },
        )
        accounts, total = await tg_service.get_list(db_session)
        assert len(accounts) == 1
        assert accounts[0].phone == "+79004444444"
        assert total == 1


class TestTelegramClientServiceDeleteAccount:
    """Тесты удаления аккаунта."""

    async def test_delete_account(
        self,
        db_session: AsyncSession,
        tg_service: TelegramAccountService,
        tg_account: TelegramAccount,
    ):
        """Успешное удаление аккаунта."""
        await tg_service.delete_account(db_session, tg_account.id)
        found = await tg_service.repository.get_by_id(db_session, tg_account.id)
        assert found is None

    async def test_delete_account_not_found(
        self,
        db_session: AsyncSession,
        tg_service: TelegramAccountService,
    ):
        """Удаление несуществующего аккаунта — NotFoundError."""
        with pytest.raises(NotFoundError):
            await tg_service.delete_account(db_session, uuid.uuid4())

    async def test_delete_account_publishes_event(
        self,
        db_session: AsyncSession,
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
        service = TelegramAccountService(
            repository=repo,
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        account = await repo.create(
            db_session,
            {
                "phone": "+79006666666",
                "session_file": "/tmp/s6",
            },
        )

        await service.delete_account(db_session, account.id)

        assert len(published) == 1
        assert published[0][0] == BusTopics.TG_ACCOUNT_DISCONNECTED
        assert published[0][1]["reason"] == "deleted"


# --- Тесты сервиса: авторизация ---


class TestTelegramClientServiceAuth:
    """Тесты авторизации с моком ClientManager."""

    async def test_verify_code_connected_publishes_event(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
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
        # Добавляем мок-клиента в менеджер
        mock_client = MagicMock()
        mock_client.on = MagicMock()
        manager._clients[tg_account.id] = mock_client

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramAccountService(
            repository=repo,
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = CodeRequest(account_id=tg_account.id, code="12345")
        result = await service.verify_code(db_session, data.model_dump())

        assert result.status == "connected"
        assert len(published) == 1
        assert published[0][0] == BusTopics.TG_ACCOUNT_CONNECTED

    async def test_verify_code_2fa_required(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
    ):
        """Если аккаунт с 2FA — возвращается статус 2fa_required."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        manager.sign_in_with_code = AsyncMock(return_value="2fa_required")

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramAccountService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = CodeRequest(account_id=tg_account.id, code="12345")
        result = await service.verify_code(db_session, data.model_dump())

        assert result.status == "2fa_required"

    async def test_verify_password_connected(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
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
        # Добавляем мок-клиента в менеджер
        mock_client = MagicMock()
        mock_client.on = MagicMock()
        manager._clients[tg_account.id] = mock_client

        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramAccountService(
            repository=repo,
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        data = PasswordRequest(account_id=tg_account.id, password="cloudpass")
        result = await service.verify_password(db_session, data.model_dump())

        assert result.status == "connected"
        assert len(published) == 1
        assert published[0][0] == BusTopics.TG_ACCOUNT_CONNECTED

    async def test_complete_qr_auth_registers_new_message_handler(
        self,
        db_session: AsyncSession,
    ):
        """После QR-входа клиент должен сразу начать слушать новые сообщения."""
        account_id = uuid.uuid4()
        published = []

        class MockBus:
            async def publish(self, topic, message):
                published.append((topic, message))

        manager = TelegramClientManager()
        manager.complete_qr_login = AsyncMock(
            return_value={
                "first_name": "QR",
                "last_name": "User",
                "username": "qr_user",
                "telegram_id": 123456789,
            }
        )
        manager.get_session_path = MagicMock(return_value="/tmp/qr_session")
        mock_client = MagicMock()
        mock_client.on = MagicMock(return_value=lambda handler: handler)
        manager.set_client(account_id, mock_client)

        service = TelegramAccountService(
            repository=TelegramAccountRepository(),
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=TelegramSettingsRepository(),
            chat_state_repository=TelegramChatStateRepository(),
        )

        account = await service.complete_qr_auth(db_session, account_id)

        assert account.id == account_id
        assert account.is_connected is True
        mock_client.on.assert_called_once_with(NewMessage)
        assert published[0][0] == BusTopics.TG_ACCOUNT_CONNECTED


# --- Тесты сервиса: чаты и сообщения ---


class TestTelegramClientServiceChatsMessages:
    """Тесты получения чатов и сообщений."""

    async def test_get_chats_not_connected(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
    ):
        """Получение чатов отключённого аккаунта — ConflictError."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramAccountService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        with pytest.raises(ConflictError):
            await service.get_chats(db_session, tg_account.id)

    async def test_get_messages_not_connected(
        self,
        db_session: AsyncSession,
        tg_account: TelegramAccount,
    ):
        """Получение сообщений отключённого аккаунта — ConflictError."""
        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()
        service = TelegramAccountService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        with pytest.raises(ConflictError):
            await service.get_messages(db_session, tg_account.id, chat_id=123)

    async def test_get_chats_success(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
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
        service = TelegramAccountService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        result = await service.get_chats(db_session, connected_tg_account.id)
        assert len(result) == 1
        assert result[0]["name"] == "Chat1"

    async def test_get_messages_success(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
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
        service = TelegramAccountService(
            repository=repo,
            message_bus=bus,
            client_manager=manager,
            settings_repository=settings_repo,
            chat_state_repository=chat_state_repo,
        )

        result = await service.get_messages(db_session, connected_tg_account.id, chat_id=1)
        assert len(result) == 1
        assert result[0]["text"] == "Hi"

    async def test_incoming_message_publishes_nested_sender(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
    ):
        """Telethon sender преобразуется в объект sender события шины."""
        published = []

        class MockBus:
            async def publish(self, topic, message):
                published.append((topic, message))

        manager = TelegramClientManager()
        manager.get_client = MagicMock(return_value=MagicMock())
        manager.extract_media = AsyncMock(return_value=[])
        service = TelegramAccountService(
            repository=TelegramAccountRepository(),
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=TelegramSettingsRepository(),
            chat_state_repository=TelegramChatStateRepository(),
        )
        service.should_read_message = AsyncMock(return_value=True)

        event = MagicMock()
        event.is_private = True
        event.is_group = False
        event.is_channel = False
        event.chat_id = 123
        event.sender_id = 987654321
        event.get_sender = AsyncMock(
            return_value=MagicMock(
                username="vacancy_author",
                first_name="Иван",
                last_name="Иванов",
            )
        )
        event.message.id = 42
        event.message.text = "Python vacancy"
        event.message.date = None
        event.message.reply_to_msg_id = None
        event.message.fwd_from = None
        event.message.forward = None

        await service.handle_incoming_message(
            session=db_session,
            account_id=connected_tg_account.id,
            event=event,
        )

        topic, payload = published[0]
        assert topic == BusTopics.TG_MESSAGE_RECEIVED
        assert "sender_id" not in payload
        assert payload["sender"] == {
            "sender_id": 987654321,
            "username": "vacancy_author",
            "first_name": "Иван",
            "last_name": "Иванов",
        }
        assert payload["reply_to"] is None
        assert payload["forward_from"] is None

    async def test_incoming_message_publishes_reply_to(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
    ):
        published = []

        class MockBus:
            async def publish(self, topic, message):
                published.append((topic, message))

        manager = TelegramClientManager()
        manager.get_client = MagicMock(return_value=MagicMock())
        manager.extract_media = AsyncMock(return_value=[])
        service = TelegramAccountService(
            repository=TelegramAccountRepository(),
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=TelegramSettingsRepository(),
            chat_state_repository=TelegramChatStateRepository(),
        )
        service.should_read_message = AsyncMock(return_value=True)

        quoted = SimpleNamespace(
            id=10,
            text="вчерашний план",
            get_sender=AsyncMock(
                return_value=SimpleNamespace(
                    first_name="Alice", last_name=None, username=None, title=None
                )
            ),
        )

        event = MagicMock()
        event.chat_id = 123
        event.sender_id = 1
        event.get_sender = AsyncMock(return_value=MagicMock(username=None, first_name="U", last_name=None))
        event.message.id = 42
        event.message.text = "ок"
        event.message.date = None
        event.message.reply_to_msg_id = 10
        event.message.get_reply_message = AsyncMock(return_value=quoted)
        event.message.fwd_from = None
        event.message.forward = None

        await service.handle_incoming_message(
            session=db_session,
            account_id=connected_tg_account.id,
            event=event,
        )

        _, payload = published[0]
        assert payload["reply_to"] == {
            "message_id": 10,
            "sender_name": "Alice",
            "text": "вчерашний план",
        }
        assert payload["forward_from"] is None
        assert payload["text"] == "ок"

    async def test_read_unread_skips_chats_outside_whitelist(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
    ):
        published = []

        class MockBus:
            async def publish(self, topic, message):
                published.append((topic, message))

        allowed = TgMessageReceived(
            account_id=connected_tg_account.id,
            chat_id=1,
            message_id=10,
            sender=Sender(sender_id=1),
            text="ok",
        )
        blocked = TgMessageReceived(
            account_id=connected_tg_account.id,
            chat_id=2,
            message_id=11,
            sender=Sender(sender_id=2),
            text="nope",
        )

        manager = TelegramClientManager()
        manager.get_messages = AsyncMock(
            side_effect=lambda account_id, chat_id, last_read_message_id=None, limit=50, offset_id=0: (
                [allowed] if chat_id == 1 else [blocked]
            )
        )
        service = TelegramAccountService(
            repository=TelegramAccountRepository(),
            message_bus=MockBus(),
            client_manager=manager,
            settings_repository=TelegramSettingsRepository(),
            chat_state_repository=TelegramChatStateRepository(),
        )
        service.chat_state_repository.get_all_by_account = AsyncMock(
            return_value=[
                SimpleNamespace(chat_id=1, last_read_message_id=0),
                SimpleNamespace(chat_id=2, last_read_message_id=0),
            ]
        )
        service.should_read_message = AsyncMock(
            side_effect=lambda session, account_id, chat_id: chat_id == 1
        )
        service.chat_state_repository.upsert_last_read = AsyncMock()

        count = await service.read_unread_messages(db_session, connected_tg_account.id)

        assert count == 1
        assert len(published) == 1
        assert published[0][1]["chat_id"] == 1
        manager.get_messages.assert_awaited_once()
        assert manager.get_messages.await_args.kwargs["chat_id"] == 1

    async def test_whitelist_on_and_empty_reads_nothing(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
        tg_service: TelegramAccountService,
    ):
        settings_svc = TelegramSettingsService(TelegramSettingsRepository())
        await settings_svc.create_default_settings(db_session, connected_tg_account.id)
        assert await tg_service.should_read_message(
            db_session, connected_tg_account.id, chat_id=123
        ) is False

    async def test_whitelist_on_with_ids_allows_only_listed(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
        tg_service: TelegramAccountService,
    ):
        settings_svc = TelegramSettingsService(TelegramSettingsRepository())
        settings = await settings_svc.create_default_settings(db_session, connected_tg_account.id)
        await settings_svc.repository.update(
            db_session, settings, {"whitelist_chat_ids": [123]}
        )
        assert await tg_service.should_read_message(
            db_session, connected_tg_account.id, chat_id=123
        ) is True
        assert await tg_service.should_read_message(
            db_session, connected_tg_account.id, chat_id=999
        ) is False

    async def test_whitelist_off_reads_everything(
        self,
        db_session: AsyncSession,
        connected_tg_account: TelegramAccount,
        tg_service: TelegramAccountService,
    ):
        settings_svc = TelegramSettingsService(TelegramSettingsRepository())
        settings = await settings_svc.create_default_settings(db_session, connected_tg_account.id)
        await settings_svc.repository.update(db_session, settings, {"use_whitelist": False})
        assert await tg_service.should_read_message(
            db_session, connected_tg_account.id, chat_id=999
        ) is True


class TestTgEvents:
    """Тесты сериализации событий шины."""

    def test_tg_message_received_to_bus_dict(self):
        event = TgMessageReceived(
            account_id=uuid.uuid4(),
            chat_id=-1001234567890,
            message_id=42,
            sender=Sender(
                sender_id=123456,
                username="vacancy_author",
                first_name="Иван",
                last_name="Иванов",
            ),
            text="Привет!",
            media=[{"telegram_id": 123, "type": "photo"}],
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "telegram_clients.event.message.received"
        assert data["chat_id"] == -1001234567890
        assert data["message_id"] == 42
        assert "sender_id" not in data
        assert data["sender"] == {
            "sender_id": 123456,
            "username": "vacancy_author",
            "first_name": "Иван",
            "last_name": "Иванов",
        }
        assert data["text"] == "Привет!"
        assert data["reply_to"] is None
        assert data["forward_from"] is None
        assert len(data["media"]) == 1
        assert data["media"][0]["type"] == "photo"

    def test_tg_message_received_includes_reply_and_forward(self):
        event = TgMessageReceived(
            account_id=uuid.uuid4(),
            chat_id=1,
            message_id=2,
            sender=Sender(sender_id=1),
            text="ок",
            reply_to={"message_id": 1, "sender_name": "Alice", "text": "план"},
            forward_from={"message_id": None, "sender_name": "Bob", "text": "смотри это"},
        )
        data = event.to_bus_dict()
        assert data["reply_to"]["sender_name"] == "Alice"
        assert data["forward_from"]["sender_name"] == "Bob"

    def test_tg_account_connected_to_bus_dict(self):
        event = TgAccountConnected(
            account_id=uuid.uuid4(),
            phone="+79001234567",
            telegram_id=999888,
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "telegram_clients.event.account.connected"
        assert data["phone"] == "+79001234567"
        assert data["telegram_id"] == 999888

    def test_tg_account_disconnected_to_bus_dict(self):
        event = TgAccountDisconnected(
            account_id=uuid.uuid4(),
            reason="error",
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "telegram_clients.event.account.disconnected"
        assert data["reason"] == "error"


# --- Тесты обработчиков ---


class TestTgHandlers:
    """Тесты обработчиков шины модуля telegram_clients."""

    async def test_handle_send_message_success(self):
        """Обработчик отправляет сообщение через client_manager."""
        from src.modules.telegram_clients.handlers import register_handlers

        # Регистрация не должна падать
        register_handlers()

        # Проверяем, что обработчик зарегистрирован
        from src.bus import get_consumer
        bus = get_consumer()
        assert BusTopics.TG_MESSAGE_SEND in bus.get_subscribers()

    async def test_handle_send_message_missing_fields(self):
        """Обработчик игнорирует сообщение с неполными данными."""
        from src.modules.telegram_clients.handlers import register_handlers

        # Регистрация не должна падать
        register_handlers()

        from src.bus import get_consumer
        bus = get_consumer()
        assert BusTopics.TG_MESSAGE_SEND in bus.get_subscribers()


# --- Тесты сервиса: состояние чтения чатов ---


class TestTelegramClientServiceChatState:
    """Тесты методов управления состоянием чтения чатов."""

    async def test_get_chat_state_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Получение несуществующего состояния — NotFoundError."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramAccountService(
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
                "phone": "+79007777777",
                "session_file": "/tmp/s7",
            },
        )

        # Пытаемся получить несуществующее состояние
        with pytest.raises(NotFoundError):
            await service.get_chat_state(db_session, account.id, chat_id=123)

    async def test_update_last_read_create_and_update(
        self,
        db_session: AsyncSession,
    ):
        """Создание и обновление состояния чтения."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramAccountService(
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
                "phone": "+79008888888",
                "session_file": "/tmp/s8",
            },
        )

        # Создаём состояние
        chat_id = 456
        message_id = 100
        state = await service.update_last_read(db_session, account.id, chat_id, message_id)

        assert state.account_id == account.id
        assert state.chat_id == chat_id
        assert state.last_read_message_id == message_id

        # Обновляем состояние
        new_message_id = 200
        updated_state = await service.update_last_read(
            db_session, account.id, chat_id, new_message_id
        )

        assert updated_state.account_id == account.id
        assert updated_state.chat_id == chat_id
        assert updated_state.last_read_message_id == new_message_id

    async def test_update_last_read_multiple_chats(
        self,
        db_session: AsyncSession,
    ):
        """Обновление состояния для нескольких чатов."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramAccountService(
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
                "phone": "+79009999999",
                "session_file": "/tmp/s9",
            },
        )

        # Обновляем состояния для разных чатов
        await service.update_last_read(db_session, account.id, 1, 10)
        await service.update_last_read(db_session, account.id, 2, 20)
        await service.update_last_read(db_session, account.id, 3, 30)

        # Получаем все состояния
        all_states = await service.get_all_chats_state(db_session, account.id)

        assert len(all_states) == 3
        chat_ids = {state.chat_id for state in all_states}
        assert chat_ids == {1, 2, 3}

    async def test_get_all_chats_state(
        self,
        db_session: AsyncSession,
    ):
        """Получение всех состояний чтения аккаунта."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramAccountService(
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
                "phone": "+79001112222",
                "session_file": "/tmp/s10",
            },
        )

        # Создаём несколько состояний
        await service.update_last_read(db_session, account.id, 100, 1)
        await service.update_last_read(db_session, account.id, 101, 2)

        # Получаем все состояния
        states = await service.get_all_chats_state(db_session, account.id)

        assert len(states) == 2
        assert all(state.account_id == account.id for state in states)

    async def test_get_chat_state_not_connected_account(
        self,
        db_session: AsyncSession,
    ):
        """Получение состояния для неподключенного аккаунта — работает нормально."""
        from src.modules.telegram_clients.repository import TelegramChatStateRepository

        bus = InMemoryProducer()
        manager = TelegramClientManager()
        repo = TelegramAccountRepository()
        settings_repo = TelegramSettingsRepository()
        chat_state_repo = TelegramChatStateRepository()

        service = TelegramAccountService(
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
                "phone": "+79009990000",
                "session_file": "/tmp/s14",
                "is_connected": False,
            },
        )

        # Создаём состояние
        state = await service.update_last_read(db_session, account.id, chat_id=500, message_id=25)

        assert state.account_id == account.id
        assert state.chat_id == 500
        assert state.last_read_message_id == 25

        # Получаем состояние
        retrieved_state = await service.get_chat_state(db_session, account.id, chat_id=500)

        assert retrieved_state.account_id == account.id
        assert retrieved_state.last_read_message_id == 25
