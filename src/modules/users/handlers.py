"""
Обработчики событий модуля пользователей.

Подписываются на события из шины сообщений.
Реагируют на события из модуля auth без прямого импорта —
только через топики шины (Event-Driven Architecture).
"""

import logging

from src.bus import get_producer
from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics

logger = logging.getLogger(__name__)


def register_handlers() -> None:
    """
    Регистрация обработчиков событий на шину.

    Вызывается при старте приложения. Каждый обработчик
    подписывается на конкретный топик и реагирует
    на события от других модулей.
    """
    bus = get_producer()

    @bus.subscribe(BusTopics.USER_REGISTERED)
    async def handle_user_registered(message: dict) -> None:
        """Реакция на регистрацию нового пользователя."""
        logger.info(
            "Новый пользователь зарегистрирован: auth_id=%s, identifier=%s",
            message.get("auth_id"),
            message.get("identifier"),
        )

    @bus.subscribe(BusTopics.USER_LOGGED_IN)
    async def handle_user_logged_in(message: dict) -> None:
        """Реакция на вход пользователя."""
        logger.info(
            "Пользователь вошёл в систему: auth_id=%s, identifier=%s",
            message.get("auth_id"),
            message.get("identifier"),
        )

    @bus.subscribe(BusTopics.PROFILE_CREATED)
    async def handle_profile_created(message: dict) -> None:
        """Реакция на создание профиля."""
        logger.info(
            "Профиль создан: auth_id=%s, profile_id=%s",
            message.get("auth_id"),
            message.get("profile_id"),
        )

    @bus.subscribe(BusTopics.PROFILE_UPDATED)
    async def handle_profile_updated(message: dict) -> None:
        """Реакция на обновление профиля."""
        logger.info(
            "Профиль обновлён: auth_id=%s, fields=%s",
            message.get("auth_id"),
            message.get("fields_updated"),
        )

    @bus.subscribe(BusTopics.PROFILE_DELETED)
    async def handle_profile_deleted(message: dict) -> None:
        """Реакция на удаление профиля."""
        logger.info(
            "Профиль удалён: auth_id=%s, profile_id=%s",
            message.get("auth_id"),
            message.get("profile_id"),
        )
