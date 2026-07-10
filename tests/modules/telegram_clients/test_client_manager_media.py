"""
Тесты для загрузки медиа в storage при получении сообщений.

Используем respx для моков HTTP-запросов к storage API.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from src.core.bus_topics import BusTopics
from src.modules.telegram_clients.client_manager import TelegramClientManager


def create_mock_event(chat_id=-1001234567890, sender_id=123456789, is_private=True):
    """Создаёт мок Telethon event."""
    mock_event = MagicMock()
    mock_event.chat_id = chat_id
    mock_event.sender_id = sender_id
    mock_event.is_private = is_private
    mock_event.is_group = not is_private
    mock_event.is_channel = False
    return mock_event


# Mock session factory для всех тестов
@pytest.fixture(autouse=True)
def mock_session_factory():
    """Фикстура для мока async_session_factory."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "src.modules.telegram_clients.client_manager.async_session_factory",
        return_value=mock_session,
    ):
        yield mock_session


@pytest.mark.asyncio
@respx.mock
async def test_on_new_message_with_photo_uploads_to_storage(
    mock_session_factory,
):
    """Входящее сообщение с фото загружается в storage."""
    telegram_media_id = "AQADBAAT..."

    # Mock storage API
    respx.post("http://localhost:8000/internal/media/").mock(
        return_value=Response(
            status_code=201,
            json={
                "id": "mock-storage-id",
                "filename": f"{telegram_media_id}.dat",
                "content_type": "image/jpeg",
                "size_bytes": 1024,
                "is_public": False,
            },
        )
    )

    # Mock MessageBus
    published_messages = []

    class MockBus:
        async def publish(self, topic, message):
            published_messages.append((topic, message))

    # Mock Telethon client с правильным .on() декоратором
    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    # Mock should_read_message - всегда разрешаем чтение
    with patch.object(
        TelegramClientManager, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        # Mock download_media — возвращает bytes
        async def mock_download_media(media, bytes=True):
            return b"fake image data"

        mock_client.download_media = mock_download_media

        # Создаём менеджер с моком шины
        manager = TelegramClientManager(MockBus())
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        # Регистрируем handler
        manager._register_message_handler(account_id, mock_client)

        # Mock event
        mock_event = create_mock_event()

        # Mock message
        mock_message = MagicMock()
        mock_message.id = 42
        mock_message.text = "Привет с фото!"
        mock_message.media = MagicMock()
        mock_message.media.id = telegram_media_id
        mock_message.media.__class__.__name__ = "MessageMediaPhoto"

        mock_event.message = mock_message

        # Вызываем зарегистрированный handler
        assert len(registered_handlers) == 1
        await registered_handlers[0](mock_event)

        # Проверяем что сообщение было опубликовано
        assert len(published_messages) == 1
        topic, message = published_messages[0]

        assert topic == BusTopics.TG_MESSAGE_RECEIVED
        assert message["account_id"] == str(account_id)
        assert message["chat_id"] == -1001234567890
        assert message["message_id"] == 42
        assert message["text"] == "Привет с фото!"
        assert len(message["media"]) == 1
        assert message["media"][0]["type"] == "messagemediaphoto"
        assert message["media"][0]["id"] == telegram_media_id
        # file_id будет добавлен обработчиком шины при загрузке в storage
        assert "data" in message["media"][0]  # Данные для обработки


@pytest.mark.asyncio
@respx.mock
async def test_on_new_message_with_media_upload_error(
    mock_session_factory,
):
    """Входящее сообщение с медиа при ошибке загрузки имеет file_id=None."""
    # Mock storage API — ошибка 500
    respx.post("http://localhost:8000/internal/media/").mock(
        return_value=Response(status_code=500, text="Internal Server Error")
    )

    # Mock MessageBus
    published_messages = []

    class MockBus:
        async def publish(self, topic, message):
            published_messages.append((topic, message))

    # Mock Telethon client
    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    # Mock should_read_message - всегда разрешаем чтение
    with patch.object(
        TelegramClientManager, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        async def mock_download_media(media, bytes=True):
            return b"fake image data"

        mock_client.download_media = mock_download_media

        manager = TelegramClientManager(MockBus())
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        manager._register_message_handler(account_id, mock_client)

        # Mock event
        mock_event = create_mock_event()

        mock_message = MagicMock()
        mock_message.id = 42
        mock_message.text = "Сообщение с медиа"
        mock_message.media = MagicMock()
        mock_message.media.id = "media123"
        mock_message.media.__class__.__name__ = "MessageMediaDocument"

        mock_event.message = mock_message

        assert len(registered_handlers) == 1
        await registered_handlers[0](mock_event)

        # Проверяем что сообщение опубликовано
        assert len(published_messages) == 1
        topic, message = published_messages[0]

        assert topic == BusTopics.TG_MESSAGE_RECEIVED
        assert len(message["media"]) == 1
        assert message["media"][0]["id"] == "media123"
        # data есть для обработки обработчиком шины
        assert "data" in message["media"][0]


@pytest.mark.asyncio
async def test_on_new_message_without_media(
    mock_session_factory,
):
    """Входящее сообщение без медиа не загружает ничего в storage."""
    published_messages = []

    class MockBus:
        async def publish(self, topic, message):
            published_messages.append((topic, message))

    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    # Mock should_read_message - всегда разрешаем чтение
    with patch.object(
        TelegramClientManager, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        # download_media не должен вызываться
        mock_client.download_media = AsyncMock(return_value=b"should not be called")

        manager = TelegramClientManager(MockBus())
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        manager._register_message_handler(account_id, mock_client)

        mock_event = create_mock_event()

        mock_message = MagicMock()
        mock_message.id = 42
        mock_message.text = "Текстовое сообщение"
        mock_message.media = None  # Нет медиа

        mock_event.message = mock_message

        assert len(registered_handlers) == 1
        await registered_handlers[0](mock_event)

        assert len(published_messages) == 1
        topic, message = published_messages[0]

        assert topic == BusTopics.TG_MESSAGE_RECEIVED
        assert message["text"] == "Текстовое сообщение"
        assert message["media"] == []
        # download_media не должен был вызываться
        mock_client.download_media.assert_not_called()


@pytest.mark.asyncio
@respx.mock
async def test_on_new_message_with_video_uploads_to_storage(
    mock_session_factory,
):
    """Входящее сообщение с видео загружается в storage."""
    telegram_media_id = "video123"

    respx.post("http://localhost:8000/internal/media/").mock(
        return_value=Response(
            status_code=201,
            json={
                "id": "mock-video-storage-id",
                "filename": f"{telegram_media_id}.dat",
                "content_type": "video/mp4",
                "size_bytes": 2048,
                "is_public": False,
            },
        )
    )

    published_messages = []

    class MockBus:
        async def publish(self, topic, message):
            published_messages.append((topic, message))

    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    # Mock should_read_message - всегда разрешаем чтение
    with patch.object(
        TelegramClientManager, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        async def mock_download_media(media, bytes=True):
            return b"fake video data"

        mock_client.download_media = mock_download_media

        manager = TelegramClientManager(MockBus())
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        manager._register_message_handler(account_id, mock_client)

        mock_event = create_mock_event()

        mock_message = MagicMock()
        mock_message.id = 43
        mock_message.text = "Видео"
        mock_message.media = MagicMock()
        mock_message.media.id = telegram_media_id
        mock_message.media.__class__.__name__ = "MessageMediaDocument"

        mock_event.message = mock_message

        assert len(registered_handlers) == 1
        await registered_handlers[0](mock_event)

        assert len(published_messages) == 1
        topic, message = published_messages[0]

        assert topic == BusTopics.TG_MESSAGE_RECEIVED
        assert len(message["media"]) == 1
        assert message["media"][0]["type"] == "messagemediadocument"
        assert message["media"][0]["id"] == telegram_media_id
        # file_id будет добавлен обработчиком шины при загрузке в storage
        assert "data" in message["media"][0]  # Данные для обработки
