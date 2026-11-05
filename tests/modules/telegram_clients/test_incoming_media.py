"""Exercise actual Telegram callbacks and media metadata, without the removed storage API."""

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.telegram_clients.adapters.client_manager import TelegramClientManager
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.services.account import TelegramAccountService


def service_with_client(account_id):
    manager = TelegramClientManager()
    client = MagicMock()
    client.download_media = AsyncMock()
    manager.set_client(account_id, client)
    settings = AsyncMock(spec=TelegramSettingsRepository)
    settings.get_by_account_id.return_value = None
    states = AsyncMock(spec=TelegramChatStateRepository)
    producer = AsyncMock(spec=MessageProducer)
    service = TelegramAccountService(
        repository=TelegramAccountRepository(),
        message_bus=producer,
        client_manager=manager,
        settings_repository=settings,
        chat_state_repository=states,
    )
    return service, manager, client, producer, states


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["photo", "video", "voice", None])
async def test_registered_callback_publishes_real_incoming_media(db_session, monkeypatch, kind):
    account_id = uuid.uuid4()
    service, manager, client, producer, states = service_with_client(account_id)
    callbacks = []

    def register(_event):
        def capture(handler):
            callbacks.append(handler)
            return handler

        return capture

    client.on.side_effect = register

    @asynccontextmanager
    async def session_factory():
        yield db_session

    monkeypatch.setattr(
        "src.modules.telegram_clients.services.account.create_async_session", session_factory
    )
    media = None
    if kind:
        media = SimpleNamespace(
            photo=SimpleNamespace(id=99) if kind == "photo" else None,
            document=SimpleNamespace(id=99) if kind != "photo" else None,
        )
    message = SimpleNamespace(
        id=42,
        text="hello",
        date=datetime(2026, 1, 1, tzinfo=UTC),
        media=media,
        voice=kind == "voice",
        audio=None,
    )
    event = SimpleNamespace(
        chat_id=123,
        sender_id=456,
        message=message,
        get_sender=AsyncMock(
            return_value=SimpleNamespace(username="sender", first_name="Test", last_name=None)
        ),
    )
    service.register_message_handler(account_id)
    assert len(callbacks) == 1
    await callbacks[0](event)
    producer.publish.assert_awaited_once()
    topic, payload = producer.publish.await_args.args
    assert topic == BusTopics.TG_MESSAGE_RECEIVED
    assert payload["account_id"] == str(account_id)
    assert payload["text"] == "hello"
    assert payload["sender"]["sender_id"] == 456
    if kind:
        assert payload["media"][0]["telegram_id"] == 99
        if kind == "voice":
            assert payload["media"][0]["type"] == "voice"
    else:
        assert payload["media"] == []
    states.upsert_last_read.assert_awaited_once_with(
        session=db_session,
        account_id=account_id,
        chat_id=123,
        message_id=42,
    )
    client.download_media.assert_not_awaited()


@pytest.mark.asyncio
async def test_whitelist_rejects_message_before_media_or_bus_work(db_session):
    account_id = uuid.uuid4()
    service, manager, client, producer, states = service_with_client(account_id)
    service.settings_repository.get_by_account_id.return_value = SimpleNamespace(
        use_whitelist=True,
        whitelist_chat_ids=["999"],
    )
    manager.extract_media = AsyncMock()
    await service.handle_incoming_message(db_session, account_id, SimpleNamespace(chat_id=123))
    manager.extract_media.assert_not_awaited()
    producer.publish.assert_not_awaited()
    states.upsert_last_read.assert_not_awaited()


@pytest.mark.asyncio
async def test_download_voice_uses_telethon(tmp_path):
    manager = TelegramClientManager()
    account_id = uuid.uuid4()
    target = tmp_path / "out.ogg"
    target.write_bytes(b"ogg")
    client = AsyncMock()
    client.get_messages.return_value = SimpleNamespace(id=5)
    client.download_media.return_value = str(target)
    manager.set_client(account_id, client)
    assert await manager.download_voice(account_id, 1, 5) == target
    client.get_messages.assert_awaited()
    client.download_media.assert_awaited()


@pytest.mark.asyncio
async def test_login_does_not_log_phone_codes_or_hashes(caplog):
    import logging

    manager = TelegramClientManager()
    account_id = uuid.uuid4()
    client = AsyncMock()
    manager.set_client(account_id, client)
    manager._phones[account_id] = "+70000000000"
    manager._phone_code_hashes[account_id] = "test-only-sensitive-hash"
    with caplog.at_level(logging.INFO):
        assert (
            await manager.sign_in_with_code(account_id, "test-only-sensitive-code") == "connected"
        )
    assert "test-only-sensitive-code" not in caplog.text
    assert "test-only-sensitive-hash" not in caplog.text
    assert "+70000000000" not in caplog.text
    client.sign_in.assert_awaited_once_with(
        phone="+70000000000",
        code="test-only-sensitive-code",
        phone_code_hash="test-only-sensitive-hash",
    )
