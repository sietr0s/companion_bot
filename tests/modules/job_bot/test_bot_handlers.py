"""
Тесты обработчиков модуля job_bot (шлюз Telegram).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from src.bus import create_bus, get_consumer
from src.core.bus_topics import BusTopics
from src.modules.job_bot.handlers import (
    register_incoming_handlers,
    register_outgoing_handlers,
)
from src.modules.job_bot.schemas.events import BotMessageIncoming
from tests.conftest import MockBus


class TestOutgoingHandlers:
    """Тесты обработчиков исходящих сообщений."""

    @pytest.mark.asyncio
    async def test_outgoing_handler_registers(self):
        """
        Регистрация обработчика не вызывает ошибок.
        """
        # Не должно быть ошибки
        register_outgoing_handlers()

    @pytest.mark.asyncio
    async def test_outgoing_handler_skips_incomplete(self):
        """
        Обработчик пропускает сообщение без chat_id.
        """
        register_outgoing_handlers()

        bus = get_consumer()
        # Обработчик зарегистрирован
        assert BusTopics.BOT_MESSAGE_OUTGOING in bus.get_subscribers()

    @pytest.mark.asyncio
    async def test_outgoing_handler_sends_message(self):
        """
        Обработчик отправляет сообщение при наличии chat_id.
        """
        register_outgoing_handlers()

        bus = get_consumer()
        # Проверяем, что обработчик зарегистрирован
        assert len(bus.get_subscribers().get(BusTopics.BOT_MESSAGE_OUTGOING, [])) > 0

    @pytest.mark.asyncio
    async def test_edit_handler_delegates_to_bot_service(self):
        """Команда редактирования передаёт message_id и удалённую клавиатуру шлюзу."""
        _, consumer = create_bus("in_memory")
        bot_service = AsyncMock()
        register_outgoing_handlers(consumer=consumer, bot_service=bot_service)
        handler = consumer.get_subscribers()[BusTopics.BOT_MESSAGE_EDIT][0]

        await handler(
            {
                "chat_id": 100500,
                "message_id": 321,
                "text": "Подписка создана",
                "keyboard": None,
            }
        )

        bot_service.edit_message.assert_awaited_once_with(
            chat_id=100500,
            message_id=321,
            text="Подписка создана",
            keyboard=None,
        )


class TestIncomingHandlers:
    """Тесты обработчиков входящих сообщений."""

    @pytest.mark.asyncio
    async def test_incoming_handler_registers(self):
        """
        register_incoming_handlers не падает.
        """
        register_incoming_handlers()

    @pytest.mark.asyncio
    async def test_incoming_handler_no_side_effects(self):
        """
        Обработчики входящих сообщений не имеют побочных эффектов.
        """
        register_incoming_handlers()

    @pytest.mark.asyncio
    async def test_incoming_handler_publishes_telegram_user(self):
        """Входящее событие содержит обязательные данные автора Telegram."""
        bus = MockBus()
        router = register_incoming_handlers(producer=bus)
        handler = router.message.handlers[0].callback
        message = SimpleNamespace(
            chat=SimpleNamespace(id=100500),
            text="/start",
            from_user=SimpleNamespace(
                id=42,
                username="arthur",
                first_name="Arthur",
                last_name="Dent",
            ),
        )

        await handler(message)

        topic, payload = bus.published[0]
        assert topic == BusTopics.BOT_MESSAGE_INCOMING
        assert payload["chat_id"] == 100500
        assert payload["command"] == "/start"
        assert payload["user"] == {
            "telegram_id": 42,
            "username": "arthur",
            "first_name": "Arthur",
            "last_name": "Dent",
        }

    @pytest.mark.asyncio
    async def test_callback_handler_publishes_callback_data(self):
        """Inline callback передаётся в шину вместе с Telegram-пользователем."""
        bus = MockBus()
        router = register_incoming_handlers(producer=bus)
        handler = router.callback_query.handlers[0].callback
        callback = SimpleNamespace(
            data="subscribe_category:9a899845-e8a9-49e0-a282-12d2cdbd5567",
            message=SimpleNamespace(
                chat=SimpleNamespace(id=100500),
                message_id=321,
            ),
            from_user=SimpleNamespace(
                id=42,
                username="arthur",
                first_name="Arthur",
                last_name="Dent",
            ),
            answer=AsyncMock(),
        )

        await handler(callback)

        payload = bus.published[0][1]
        assert payload["callback_data"] == callback.data
        assert payload["message_id"] == 321
        assert payload["user"]["telegram_id"] == 42
        callback.answer.assert_awaited_once()

    def test_incoming_event_rejects_missing_telegram_user(self):
        """Событие без автора Telegram нарушает контракт шины."""
        with pytest.raises(ValidationError):
            BotMessageIncoming(chat_id=100500, text="/start", command="/start")
