"""
Диспетчер Telegram-бота (aiogram).

Создаёт экземпляр Bot и Dispatcher.
Поддерживает два режима: polling (по умолчанию) и webhook.
"""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bus.interface import MessageBus
from src.core.config import settings
from src.modules.job_bot.handlers import (
    register_incoming_handlers,
    register_outgoing_handlers,
)
from src.modules.job_bot.service import BotService

logger = logging.getLogger(__name__)


def create_bot(token: str = settings.TG_BOT_TOKEN) -> Bot:
    """Создать экземпляр Telegram-бота."""
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_bot_service(bot: Bot) -> BotService:
    """Создать сервис для отправки сообщений."""
    return BotService(bot=bot)


def create_dispatcher(bus: MessageBus, bot_service: BotService) -> Dispatcher:
    """
    Создать диспетчер и зарегистрировать обработчики.

    Регистрирует:
    - aiogram-обработчики входящих сообщений (публикуют в шину)
    - обработчики шины исходящих сообщений (отправляют через Telegram API)
    """
    dp = Dispatcher()

    # Регистрация обработчиков шины (исходящие сообщения)
    register_outgoing_handlers(bus, bot_service)

    # Регистрация aiogram-обработчиков (входящие сообщения)
    incoming_router = register_incoming_handlers(bus)
    dp.include_router(incoming_router)

    return dp


async def start_polling(bot: Bot, dp: Dispatcher) -> None:
    """Запустить бота в режиме polling."""
    logger.info("Запуск Telegram-бота в режиме polling")
    await dp.start_polling(bot, skip_updates=True)


async def start_webhook(
    bot: Bot,
    dp: Dispatcher,
    webhook_url: str,
    webhook_secret: str,
) -> None:
    """Запустить бота в режиме webhook."""
    logger.info("Запуск Telegram-бота в режиме webhook: %s", webhook_url)
    await bot.set_webhook(
        url=webhook_url,
        secret_token=webhook_secret,
    )
    # Webhook-роутер регистрируется в main.py как FastAPI-роут
