"""
DI-зависимости модуля job_bot.

Фабрики для создания сервисов и репозиториев модуля.
Модуль job_bot — транспортный шлюз (aiogram), не содержит
бизнес-логики. Зависимости других модулей (job_matcher)
размещаются в их собственных dependencies.py.
"""

from collections.abc import Callable
from functools import lru_cache

from aiogram import Bot

from src.core.config import settings
from src.modules.job_bot.bot import create_bot, create_bot_service
from src.modules.job_bot.service import BotService


@lru_cache
def get_bot() -> Bot:
    """Создаёт и кеширует экземпляр Telegram-бота."""
    return create_bot(token=settings.TG_BOT_TOKEN)


@lru_cache
def get_bot_service() -> BotService:
    """Создаёт и кеширует сервис для отправки сообщений через бота."""
    bot = get_bot()
    return create_bot_service(bot=bot)


# Фабрика для использования в main.py (совместимость с DI-контейнером)
def get_bot_service_factory() -> Callable[[], BotService]:
    """Возвращает фабрику для получения BotService через DI."""
    return get_bot_service
