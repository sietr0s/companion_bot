"""
Тесты BotService — отправка сообщений через Telegram-бота.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.job_bot.service import BotService


class TestBotService:
    """Тесты BotService."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """send_message успешно отправляет сообщение."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()

        service = BotService(bot=mock_bot)
        await service.send_message(
            chat_id=12345,
            text="Привет!",
        )

        mock_bot.send_message.assert_awaited_once_with(
            chat_id=12345,
            text="Привет!",
        )

    @pytest.mark.asyncio
    async def test_send_message_with_keyboard(self):
        """send_message с клавиатурой."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()

        service = BotService(bot=mock_bot)
        await service.send_message(
            chat_id=12345,
            text="Меню",
            keyboard={
                "inline_keyboard": [
                    [
                        {
                            "text": "Backend",
                            "callback_data": "subscribe_category:123",
                        }
                    ]
                ]
            },
        )

        mock_bot.send_message.assert_awaited_once()
        reply_markup = mock_bot.send_message.await_args.kwargs["reply_markup"]
        assert reply_markup.inline_keyboard[0][0].text == "Backend"
        assert reply_markup.inline_keyboard[0][0].callback_data == "subscribe_category:123"

    @pytest.mark.asyncio
    async def test_send_message_skips_empty_data(self):
        """send_message пропускает пустые данные."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()

        service = BotService(bot=mock_bot)
        await service.send_message(
            chat_id=None,
            text="",
        )

        mock_bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_message_handles_error(self):
        """send_message не падает при ошибке отправки."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))

        service = BotService(bot=mock_bot)
        # Не должно быть исключения
        await service.send_message(
            chat_id=12345,
            text="Тест",
        )

    @pytest.mark.asyncio
    async def test_edit_message_replaces_text_and_keyboard(self):
        """edit_message заменяет исходное сообщение и может удалить клавиатуру."""
        mock_bot = MagicMock()
        mock_bot.edit_message_text = AsyncMock()

        service = BotService(bot=mock_bot)
        await service.edit_message(
            chat_id=12345,
            message_id=77,
            text="Подписка создана",
            keyboard=None,
        )

        mock_bot.edit_message_text.assert_awaited_once_with(
            chat_id=12345,
            message_id=77,
            text="Подписка создана",
            reply_markup=None,
        )

    @pytest.mark.asyncio
    async def test_send_offer(self):
        """send_offer отправляет форматированное предложение."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()

        service = BotService(bot=mock_bot)
        await service.send_offer(
            chat_id=12345,
            title="Python Developer",
            description="Описание вакансии",
            tags=["python", "backend"],
            salary_from=100000,
            salary_to=200000,
            location="Москва",
        )

        mock_bot.send_message.assert_awaited_once()
        args, kwargs = mock_bot.send_message.call_args
        assert kwargs["chat_id"] == 12345
        assert "Python Developer" in kwargs["text"]
        assert "100000" in kwargs["text"]
