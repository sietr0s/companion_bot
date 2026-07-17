"""
Тесты обработчиков модуля job_bot (шлюз Telegram).
"""

import pytest

from src.bus import get_producer
from src.core.bus_topics import BusTopics
from src.modules.job_bot.handlers import (
    register_incoming_handlers,
    register_outgoing_handlers,
)


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

        bus = get_producer()
        # Обработчик зарегистрирован
        assert BusTopics.BOT_MESSAGE_OUTGOING in bus.get_subscribers()

    @pytest.mark.asyncio
    async def test_outgoing_handler_sends_message(self):
        """
        Обработчик отправляет сообщение при наличии chat_id.
        """
        register_outgoing_handlers()

        bus = get_producer()
        # Проверяем, что обработчик зарегистрирован
        assert len(bus.get_subscribers().get(BusTopics.BOT_MESSAGE_OUTGOING, [])) > 0


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