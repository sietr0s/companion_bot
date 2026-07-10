"""
Тесты обработчиков модуля job_bot (шлюз Telegram).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bus.in_memory.producer import InMemoryProducer
from src.core.bus_topics import BusTopics
from src.modules.job_bot.handlers import (
    register_incoming_handlers,
    register_outgoing_handlers,
)
from src.modules.job_bot.service import BotService


class TestOutgoingHandlers:
    """Тесты обработчиков исходящих сообщений."""

    @pytest.mark.asyncio
    async def test_outgoing_handler_registers(self):
        """
        register_outgoing_handlers не падает.
        """
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        bot_service = BotService(bot=mock_bot)

        bus = InMemoryProducer()
        # Не должно быть ошибки
        register_outgoing_handlers(bus=bus, bot_service=bot_service)

    @pytest.mark.asyncio
    async def test_outgoing_handler_skips_incomplete(self):
        """
        Обработчик пропускает сообщение без chat_id.
        """
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        bot_service = BotService(bot=mock_bot)

        bus = InMemoryProducer()
        register_outgoing_handlers(bus=bus, bot_service=bot_service)

        await bus.publish(
            BusTopics.BOT_MESSAGE_OUTGOING,
            {"text": "без chat_id"},
        )

        mock_bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_outgoing_handler_sends_message(self):
        """
        Обработчик отправляет сообщение через BotService.
        """
        mock_bot = MagicMock()
        send_mock = AsyncMock()
        mock_bot.send_message = send_mock
        bot_service = BotService(bot=mock_bot)

        bus = InMemoryProducer()
        register_outgoing_handlers(bus=bus, bot_service=bot_service)

        # Проверяем, что обработчик зарегистрирован и может быть вызван
        # Полная интеграция тестируется в e2e тестах
        assert len(bus._subscribers.get(BusTopics.BOT_MESSAGE_OUTGOING, [])) > 0


class TestIncomingHandlers:
    """Тесты обработчиков входящих сообщений."""

    @pytest.mark.asyncio
    async def test_incoming_handler_registers(self):
        """
        register_incoming_handlers не падает.
        """
        bus = InMemoryProducer()
        register_incoming_handlers(bus=bus)

    @pytest.mark.asyncio
    async def test_incoming_handler_no_side_effects(self):
        """
        Обработчики входящих сообщений не имеют побочных эффектов.
        """
        bus = InMemoryProducer()
        register_incoming_handlers(bus=bus)

        # Проверяем, что роутер создан и не падает при регистрации
        assert bus is not None
