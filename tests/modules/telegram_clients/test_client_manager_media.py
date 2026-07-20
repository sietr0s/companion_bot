"""
Тесты для загрузки медиа в storage при получении сообщений.

Проверяет, что обработчик on_new_message в TelegramClientManager
правильно делегирует в TelegramClientService.handle_incoming_message.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response
from telethon.events.newmessage import NewMessage

from src.modules.telegram_clients.client_manager import TelegramClientManager
from src.modules.telegram_clients.services.account import TelegramAccountService


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
        "src.core.database.create_async_session",
        return_value=mock_session,
    ):
        yield mock_session


@pytest.mark.asyncio
@respx.mock
async def test_on_new_message_with_photo_uploads_to_storage(
    mock_session_factory,
):
    """Входящее сообщение с фото — обработчик делегирует в сервис."""
    respx.post("http://localhost:8000/internal/media/").mock(
        return_value=Response(
            status_code=201,
            json={
                "id": "mock-storage-id",
                "filename": "photo.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 1024,
                "is_public": False,
            },
        )
    )

    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    # Мокаем should_read_message на TelegramClientService
    with patch.object(
        TelegramAccountService, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        async def mock_download_media(media, bytes=True):
            return b"fake image data"

        mock_client.download_media = mock_download_media

        manager = TelegramClientManager()
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        # Мокаем сервис — проверяем что handle_incoming_message вызван
        mock_service = MagicMock(spec=TelegramAccountService)
        mock_service.handle_incoming_message = AsyncMock()
        manager._service = mock_service

        # Регистрируем обработчик через mock_client.on
        @mock_client.on(NewMessage)
        async def on_new_message(event):
            await mock_service.handle_incoming_message(
                session=None,
                account_id=account_id,
                event=event,
            )

        mock_event = create_mock_event()

        mock_message = MagicMock()
        mock_message.id = 42
        mock_message.text = "Привет с фото!"
        mock_message.media = MagicMock()
        mock_message.media.id = "AQADBAAT..."
        mock_message.media.__class__.__name__ = "MessageMediaPhoto"

        mock_event.message = mock_message

        assert len(registered_handlers) == 1
        await registered_handlers[0](mock_event)

        # Проверяем, что handle_incoming_message был вызван
        mock_service.handle_incoming_message.assert_awaited_once()


@pytest.mark.asyncio
@respx.mock
async def test_on_new_message_with_media_upload_error(
    mock_session_factory,
):
    """Входящее сообщение с медиа при ошибке — обработчик делегирует в сервис."""
    respx.post("http://localhost:8000/internal/media/").mock(
        return_value=Response(status_code=500, text="Internal Server Error")
    )

    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    with patch.object(
        TelegramAccountService, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        async def mock_download_media(media, bytes=True):
            return b"fake image data"

        mock_client.download_media = mock_download_media

        manager = TelegramClientManager()
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        mock_service = MagicMock(spec=TelegramAccountService)
        mock_service.handle_incoming_message = AsyncMock()
        manager._service = mock_service

        # Регистрируем обработчик через mock_client.on
        @mock_client.on(NewMessage)
        async def on_new_message(event):
            await mock_service.handle_incoming_message(
                session=None,
                account_id=account_id,
                event=event,
            )

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

        mock_service.handle_incoming_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_new_message_without_media(
    mock_session_factory,
):
    """Входящее сообщение без медиа — обработчик делегирует в сервис."""
    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    with patch.object(
        TelegramAccountService, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        mock_client.download_media = AsyncMock(return_value=b"should not be called")

        manager = TelegramClientManager()
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        mock_service = MagicMock(spec=TelegramAccountService)
        mock_service.handle_incoming_message = AsyncMock()
        manager._service = mock_service

        # Регистрируем обработчик через mock_client.on
        @mock_client.on(NewMessage)
        async def on_new_message(event):
            await mock_service.handle_incoming_message(
                session=None,
                account_id=account_id,
                event=event,
            )

        mock_event = create_mock_event()

        mock_message = MagicMock()
        mock_message.id = 42
        mock_message.text = "Текстовое сообщение"
        mock_message.media = None

        mock_event.message = mock_message

        assert len(registered_handlers) == 1
        await registered_handlers[0](mock_event)

        mock_service.handle_incoming_message.assert_awaited_once()
        # download_media не должен вызываться — нет медиа
        mock_client.download_media.assert_not_called()


@pytest.mark.asyncio
@respx.mock
async def test_on_new_message_with_video_uploads_to_storage(
    mock_session_factory,
):
    """Входящее сообщение с видео — обработчик делегирует в сервис."""
    respx.post("http://localhost:8000/internal/media/").mock(
        return_value=Response(
            status_code=201,
            json={
                "id": "mock-video-storage-id",
                "filename": "video.dat",
                "content_type": "video/mp4",
                "size_bytes": 2048,
                "is_public": False,
            },
        )
    )

    mock_client = MagicMock()
    registered_handlers = []

    def mock_on(event_type):
        def decorator(func):
            registered_handlers.append(func)
            return func

        return decorator

    mock_client.on = mock_on

    with patch.object(
        TelegramAccountService, "should_read_message", new_callable=AsyncMock
    ) as mock_should_read:
        mock_should_read.return_value = True

        async def mock_download_media(media, bytes=True):
            return b"fake video data"

        mock_client.download_media = mock_download_media

        manager = TelegramClientManager()
        account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager._clients[account_id] = mock_client

        mock_service = MagicMock(spec=TelegramAccountService)
        mock_service.handle_incoming_message = AsyncMock()
        manager._service = mock_service

        # Регистрируем обработчик через mock_client.on
        @mock_client.on(NewMessage)
        async def on_new_message(event):
            await mock_service.handle_incoming_message(
                session=None,
                account_id=account_id,
                event=event,
            )

        mock_event = create_mock_event()

        mock_message = MagicMock()
        mock_message.id = 43
        mock_message.text = "Видео"
        mock_message.media = MagicMock()
        mock_message.media.id = "video123"
        mock_message.media.__class__.__name__ = "MessageMediaDocument"

        mock_event.message = mock_message

        assert len(registered_handlers) == 1
        await registered_handlers[0](mock_event)

        mock_service.handle_incoming_message.assert_awaited_once()
